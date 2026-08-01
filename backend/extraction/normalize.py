"""Deterministic post-processing of an extracted CompanyReport.

Gemini extracts the *facts* (the absolute numbers). Everything that is a pure
arithmetic consequence of those facts — growth percentages, margin deltas — is
recomputed here so the report is always internally consistent and complete,
regardless of run-to-run variation in what the model chooses to fill.

This never invents data: a derived value is only produced when both operands it
depends on are present. Missing operands leave the derived field as None so it
still renders as "N/A".
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from models.schema import ChartSeries, CompanyReport, QuarterlyFinancial


def _pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    """Percentage change new-vs-old, or None if it can't be computed."""
    if new is None or old is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100.0, 1)


def _bps_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    """Delta in basis points for margin-style rows (both already in %)."""
    if new is None or old is None:
        return None
    return round((new - old) * 100.0, 0)


# Metric-name fragments that are NOT additive across quarters, so the
# H1 = Q1 + Q2 accounting identity must never be applied to them.
_NON_ADDITIVE = ("margin", "%", "ratio", "roe", "roce")


def _fiscal_suffix(label: Optional[str]) -> str:
    """'Q2FY26' -> 'FY26'; '' if not found."""
    if not label:
        return ""
    idx = label.upper().find("FY")
    return label[idx:] if idx != -1 else ""


def _derive_prev_quarter(report: CompanyReport) -> None:
    """Fill a missing QoQ base column via the identity Q1 = H1 - Q2.

    Results presentations report the current quarter (Q2) and half-year (H1) but
    often omit the sequential prior quarter (Q1). For additive flow metrics that
    prior quarter is exactly H1 - Q2 — an accounting identity, not a guess — so
    we can complete the QoQ column deterministically when the P&L carries the
    half-year column.
    """
    pl = report.profit_loss or {}
    if not pl:
        return
    suffix = _fiscal_suffix(report.q_current_label)  # e.g. FY26
    cur_label = report.q_current_label               # e.g. Q2FY26
    h1_label = next(
        (y for y in report.financial_years
         if y.upper().startswith("H1") and y.upper().endswith(suffix.upper())),
        None,
    )
    if not h1_label or not cur_label:
        return

    for row in report.quarterly_financials:
        if not isinstance(row, QuarterlyFinancial) or row.prev_q is not None:
            continue
        if row.is_bps or any(tok in row.metric.lower() for tok in _NON_ADDITIVE):
            continue
        cols = pl.get(row.metric)
        if not cols:
            continue
        q2 = cols.get(cur_label, row.current_q)
        h1 = cols.get(h1_label)
        if q2 is None or h1 is None:
            continue
        row.prev_q = round(h1 - q2, 2)


def _normalize_quarterly(rows: list) -> None:
    """Recompute YoY / QoQ for every quarterly row from its absolute values."""
    for row in rows:
        if not isinstance(row, QuarterlyFinancial):
            continue
        change = _bps_change if row.is_bps else _pct_change
        yoy = change(row.current_q, row.year_ago_q)
        qoq = change(row.current_q, row.prev_q)
        # Only overwrite when we could compute it; keep any model value otherwise
        # (e.g. margin rows the model may have expressed differently).
        if yoy is not None:
            row.yoy_growth = yoy
        if qoq is not None:
            row.qoq_growth = qoq


def _derive_return(report: CompanyReport) -> None:
    """Upside % = (target - CMP) / CMP, when both are present."""
    if report.return_pct is None:
        report.return_pct = _pct_change(report.target_price, report.current_price)


# --------------------------------------------------------------------------- #
# Chart derivation
#
# The page-2 combo charts used to depend entirely on the model filling
# revenue_chart / gov_chart / ebitda_chart / pat_chart. When it didn't, page 2
# rendered chart-less even though the P&L and quarterly tables were fully
# populated. The series are a pure function of numbers already extracted, so we
# build them here instead of hoping for them.
# --------------------------------------------------------------------------- #

# Period-label kinds, ordered by charting preference. A chart must not mix
# quarters with half-years or full years — the bars would be incomparable.
_PERIOD_KINDS = ("Q", "H", "FY")

_PERIOD_RE = re.compile(r"^\s*(Q([1-4])|H([12]))?\s*(?:FY)?\s*(\d{2,4})\s*$", re.I)


def _parse_period(label: str) -> Optional[Tuple[str, int, int]]:
    """'Q2FY26' -> ('Q', 2026, 2); 'H1FY25' -> ('H', 2025, 1); 'FY2025' -> ('FY', 2025, 0).

    Returns None for anything that isn't a recognisable fiscal period.
    """
    if not label:
        return None
    m = _PERIOD_RE.match(label.replace("A", "").replace("E", "")
                         if label.upper().startswith("FY") else label)
    if not m:
        return None
    q, qn, hn, year = m.group(1), m.group(2), m.group(3), m.group(4)
    y = int(year)
    if y < 100:
        y += 2000
    if qn:
        return ("Q", y, int(qn))
    if hn:
        return ("H", y, int(hn))
    if q is None:
        return ("FY", y, 0)
    return None


def _chart_periods(labels: List[str]) -> List[str]:
    """Pick the largest chronologically-sortable group of same-kind periods."""
    groups: Dict[str, List[Tuple[Tuple[str, int, int], str]]] = {}
    for lab in labels:
        parsed = _parse_period(lab)
        if parsed:
            groups.setdefault(parsed[0], []).append((parsed, lab))

    best: List[Tuple[Tuple[str, int, int], str]] = []
    for kind in _PERIOD_KINDS:
        entries = groups.get(kind, [])
        if len(entries) > len(best):
            best = entries
    if len(best) < 2:
        return []
    best.sort(key=lambda t: (t[0][1], t[0][2]))
    return [lab for _, lab in best]


def _row_values(data: Dict[str, Dict[str, Optional[float]]], metric: str,
                periods: List[str]) -> List[Optional[float]]:
    row = data.get(metric) or {}
    return [row.get(p) for p in periods]


def _find_metric(data: Dict[str, Dict[str, Optional[float]]],
                 keywords: Tuple[str, ...]) -> Optional[str]:
    """First metric label matching a keyword — exact match wins over substring."""
    labels = list(data.keys())
    lowered = {lab: lab.lower().strip() for lab in labels}
    for kw in keywords:
        for lab in labels:
            if lowered[lab] == kw:
                return lab
    for kw in keywords:
        for lab in labels:
            if kw in lowered[lab]:
                return lab
    return None


def _sequential_growth(values: List[Optional[float]]) -> List[Optional[float]]:
    """Period-on-period growth %; first point has no base so it stays None."""
    out: List[Optional[float]] = [None]
    for prev, cur in zip(values, values[1:]):
        out.append(_pct_change(cur, prev))
    return out


def _margin_line(num: List[Optional[float]], den: List[Optional[float]]) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for n, d in zip(num, den):
        out.append(round(n / d * 100.0, 1) if (n is not None and d not in (None, 0)) else None)
    return out


def _build_series(label: str, periods: List[str], bars: List[Optional[float]],
                  line: List[Optional[float]], bar_legend: str,
                  line_legend: str) -> Optional[ChartSeries]:
    """Only chart a metric with at least two real data points."""
    if sum(1 for v in bars if v is not None) < 2:
        return None
    return ChartSeries(
        label=label, periods=periods, bar_values=bars, line_values=line,
        bar_legend=bar_legend, line_legend=line_legend, line_is_percent=True,
    )


def _quarterly_as_table(report: CompanyReport) -> Tuple[List[str], Dict[str, Dict[str, Optional[float]]]]:
    """Fallback source: reshape the 3-column quarterly table into period->value rows."""
    labels = [report.q_year_ago_label, report.q_prev_label, report.q_current_label]
    getters = ("year_ago_q", "prev_q", "current_q")
    # Chronological order is year-ago, previous, current — but drop any column
    # the report didn't label, and de-duplicate repeated labels.
    cols = [(lab, attr) for lab, attr in zip(labels, getters) if lab]
    seen = set()
    cols = [(lab, attr) for lab, attr in cols if not (lab in seen or seen.add(lab))]
    if len(cols) < 2:
        return [], {}

    data: Dict[str, Dict[str, Optional[float]]] = {}
    for row in report.quarterly_financials:
        if not isinstance(row, QuarterlyFinancial):
            continue
        data[row.metric] = {lab: getattr(row, attr, None) for lab, attr in cols}
    return [lab for lab, _ in cols], data


_REVENUE_KEYS = ("revenue", "net interest income", "core operating income",
                 "total income", "net sales", "sales", "turnover")
_EBITDA_KEYS = ("ebitda", "core operating profit", "operating profit",
                "profit before tax", "pbt")
_PAT_KEYS = ("profit after tax", "adj pat", "adjusted pat", "rep. pat",
             "net profit", "pat")
_FOURTH_KEYS = ("gross order value", "gov", "total advances", "advances",
                "total deposits", "deposits", "aum", "total assets",
                "order book", "net worth")


def _derive_charts(report: CompanyReport) -> None:
    """Build any missing page-2 combo chart from already-extracted numbers."""
    periods = _chart_periods(report.financial_years)
    data = report.profit_loss or {}
    if len(periods) < 2 or not data:
        # Results decks often carry only the quarterly comparison table.
        periods, data = _quarterly_as_table(report)
    if len(periods) < 2 or not data:
        return

    rev_key = _find_metric(data, _REVENUE_KEYS)
    ebitda_key = _find_metric(data, _EBITDA_KEYS)
    pat_key = _find_metric(data, _PAT_KEYS)

    rev_vals = _row_values(data, rev_key, periods) if rev_key else []

    if report.revenue_chart is None and rev_key:
        report.revenue_chart = _build_series(
            rev_key, periods, rev_vals, _sequential_growth(rev_vals),
            f"{rev_key} (Rs.cr)", "Growth (%)")

    if report.ebitda_chart is None and ebitda_key:
        vals = _row_values(data, ebitda_key, periods)
        # Margin is the more informative line when we have a revenue base.
        line = _margin_line(vals, rev_vals) if rev_vals else _sequential_growth(vals)
        legend = "Margin (%)" if rev_vals else "Growth (%)"
        report.ebitda_chart = _build_series(
            ebitda_key, periods, vals, line, f"{ebitda_key} (Rs.cr)", legend)

    if report.pat_chart is None and pat_key:
        vals = _row_values(data, pat_key, periods)
        report.pat_chart = _build_series(
            pat_key, periods, vals, _sequential_growth(vals),
            f"{pat_key} (Rs.cr)", "Growth (%)")

    if report.gov_chart is None:
        # Fourth slot: a scale metric that isn't already charted above.
        used = {k for k in (rev_key, ebitda_key, pat_key) if k}
        for source in (data, report.balance_sheet or {}):
            key = _find_metric({k: v for k, v in source.items() if k not in used},
                               _FOURTH_KEYS)
            if not key:
                continue
            vals = _row_values(source, key, periods)
            series = _build_series(key, periods, vals, _sequential_growth(vals),
                                   f"{key} (Rs.cr)", "Growth (%)")
            if series:
                report.gov_chart = series
                break


def normalize_report(report: CompanyReport) -> CompanyReport:
    """Fill in all arithmetic-derivable fields. Mutates and returns the report."""
    _derive_prev_quarter(report)
    _normalize_quarterly(report.quarterly_financials)
    _derive_return(report)
    _derive_charts(report)
    return report
