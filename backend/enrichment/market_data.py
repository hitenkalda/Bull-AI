"""Fill N/A market fields from yfinance — best-effort, never fatal.

A company results deck contains operating data but rarely the live market
snapshot (CMP, market cap, 52-week range, beta, dividend yield) or a price
history. yfinance supplies those from the public ticker. This module fills ONLY
the fields the source left as ``None`` — extracted values are never overwritten —
and degrades to a no-op when offline, when yfinance is missing, or when the
ticker can't be resolved.

Every failure path logs a one-line reason under the ``[market-data]`` prefix.
Silent failure was the original sin here: a stale yfinance pin (0.2.40) 429'd on
every call against Yahoo's current crumb/cookie auth and the whole Company Data
block rendered N/A with no clue why. Requires yfinance >= 1.2.0.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from models.schema import CompanyReport, PriceHistory

_CR = 1e7  # 1 crore = 10,000,000 — yfinance reports absolute rupees

_LOG = "[market-data]"

# Yahoo rate-limits bursts (HTTP 429). A couple of spaced retries turns a
# transient block into a populated report instead of a page of N/A.
_RETRIES = 3
_BACKOFF_SECONDS = (1.5, 4.0)


def _log(msg: str) -> None:
    print(f"{_LOG} {msg}")


def _tickers_for(report: CompanyReport) -> List[str]:
    """Candidate yfinance symbols, NSE first (more liquid, better data)."""
    out: List[str] = []
    if report.nse_code:
        out.append(f"{report.nse_code.strip()}.NS")
    if report.bse_code:
        out.append(f"{report.bse_code.strip()}.BO")
    # Bloomberg code like "JSWENERGY:IN" -> use the symbol part on NSE.
    if report.bloomberg_code and ":" in report.bloomberg_code:
        sym = report.bloomberg_code.split(":", 1)[0].strip()
        cand = f"{sym}.NS"
        if sym and cand not in out:
            out.append(cand)
    return out


def _info_with_retry(ticker, sym: str) -> dict:
    """``ticker.get_info()`` with backoff, so one 429 doesn't blank the report."""
    for attempt in range(_RETRIES):
        try:
            info = ticker.get_info()
            if info:
                return info
            _log(f"{sym}: empty info dict (attempt {attempt + 1}/{_RETRIES})")
        except Exception as exc:
            detail = str(exc)[:120]
            _log(f"{sym}: get_info failed ({type(exc).__name__}: {detail}) "
                 f"attempt {attempt + 1}/{_RETRIES}")
        if attempt < len(_BACKOFF_SECONDS):
            time.sleep(_BACKOFF_SECONDS[attempt])
    return {}


def _first_working_ticker(candidates: List[str]) -> Tuple[object, dict]:
    """Return (yf.Ticker, info) for the first symbol that resolves, else (None, {})."""
    try:
        import yfinance as yf
    except ImportError:
        _log("yfinance is not installed — market fields stay N/A. "
             "Install with: pip install 'yfinance>=1.2.0'")
        return None, {}

    for sym in candidates:
        try:
            t = yf.Ticker(sym)
        except Exception as exc:
            _log(f"{sym}: could not construct Ticker ({type(exc).__name__})")
            continue

        info = _info_with_retry(t, sym)
        # A valid equity resolves to a price; junk symbols return an empty dict.
        if info and (info.get("currentPrice") or info.get("regularMarketPrice")
                     or info.get("previousClose")):
            _log(f"resolved {sym} ({info.get('longName') or 'unknown name'})")
            return t, info
        _log(f"{sym}: no price in info — trying next candidate")
    return None, {}


def _set_if_none(obj, attr: str, value) -> None:
    if value is None:
        return
    if getattr(obj, attr, None) is None:
        setattr(obj, attr, value)


def _rebased(series) -> List[float]:
    """Rebase a price series to 100 at its first point (stock-vs-benchmark charts)."""
    vals = [float(v) for v in series if v is not None]
    if not vals or vals[0] == 0:
        return []
    base = vals[0]
    return [round(v / base * 100.0, 2) for v in vals]


def _price_history(ticker, period: str, benchmark_symbol: str = "^NSEI",
                   max_points: int = 26) -> Optional[PriceHistory]:
    """Downsampled stock-vs-benchmark (rebased) line history, or None on failure."""
    import yfinance as yf

    try:
        hist = ticker.history(period=period, interval="1wk")
    except Exception as exc:
        _log(f"price history {period} failed ({type(exc).__name__}: {str(exc)[:100]})")
        return None
    if hist is None or hist.empty or "Close" not in hist:
        _log(f"price history {period}: no rows returned")
        return None

    closes = hist["Close"].dropna()
    if closes.empty:
        _log(f"price history {period}: all closes NaN")
        return None

    # Downsample to at most max_points evenly-spaced observations.
    n = len(closes)
    step = max(1, n // max_points)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)

    stock = [round(float(closes.iloc[i]), 2) for i in idx]
    labels = [closes.index[i].strftime("%b-%y") for i in idx]

    # Benchmark, rebased to the stock's starting level for a like-for-like line.
    bench_vals: List[Optional[float]] = []
    try:
        bench = yf.Ticker(benchmark_symbol).history(period=period, interval="1wk")
        if bench is not None and not bench.empty and "Close" in bench:
            bcloses = bench["Close"].dropna()
            if not bcloses.empty:
                bn = len(bcloses)
                bench_raw = [float(bcloses.iloc[min(i, bn - 1)]) for i in idx]
                reb = _rebased(bench_raw)
                # Scale rebased benchmark (base 100) onto the stock's starting price.
                if reb and stock:
                    scale = stock[0] / 100.0
                    bench_vals = [round(v * scale, 2) for v in reb]
    except Exception as exc:
        _log(f"benchmark {benchmark_symbol} unavailable ({type(exc).__name__}) — "
             "drawing price line only")
        bench_vals = []

    return PriceHistory(
        labels=labels,
        primary=stock,
        secondary=bench_vals,
        primary_legend="Share Price (Rs.)",
        secondary_legend="Nifty 50 (rebased)" if bench_vals else "",
    )


def _dividend_yield_pct(info: dict) -> Optional[float]:
    """Normalise dividendYield to a percent.

    yfinance changed units: <=0.2.x returned a fraction (0.0084), >=1.x returns
    a percent (0.84). Disambiguate with dividendRate/price, which is unit-stable,
    and only fall back to the magnitude heuristic when that isn't available.
    """
    dy = info.get("dividendYield")
    if dy is None:
        return None
    dy = float(dy)

    rate = info.get("dividendRate")
    price = (info.get("currentPrice") or info.get("regularMarketPrice")
             or info.get("previousClose"))
    if rate and price:
        true_pct = float(rate) / float(price) * 100.0
        # Pick whichever reading of dy matches the computed yield.
        if abs(dy - true_pct) <= abs(dy * 100.0 - true_pct):
            return round(dy, 2)
        return round(dy * 100.0, 2)

    # No cross-check available: a real equity yield above 30% is implausible,
    # so treat a small number as already-a-percent only when it is >= 0.3.
    return round(dy if dy >= 0.3 else dy * 100.0, 2)


def enrich_with_market_data(report: CompanyReport, reporter=None) -> CompanyReport:
    """Fill only the market fields the source left empty. Mutates and returns report."""
    def _note(msg: str) -> None:
        if reporter is not None:
            reporter.note("market", msg)

    candidates = _tickers_for(report)
    if not candidates:
        _log("no NSE/BSE/Bloomberg code in the extracted report — "
             "cannot look up market data")
        _note("No ticker code found in the document")
        return report

    _log(f"looking up {', '.join(candidates)}")
    _note(f"Looking up {', '.join(candidates)}")
    try:
        ticker, info = _first_working_ticker(candidates)
    except Exception as exc:
        _log(f"ticker resolution failed ({type(exc).__name__}: {str(exc)[:120]})")
        _note("Ticker lookup failed — market fields stay N/A")
        return report
    if ticker is None:
        _log("no candidate resolved — market fields stay N/A")
        _note("No ticker resolved — market fields stay N/A")
        return report
    _note(f"Resolved {info.get('symbol') or candidates[0]}")

    price = (info.get("currentPrice") or info.get("regularMarketPrice")
             or info.get("previousClose"))

    cd = report.company_data
    filled: List[str] = []
    try:
        # Header CMP (analyst target/rating stay untouched — opinions, not data).
        if report.current_price is None and price:
            report.current_price = round(float(price), 2)
            filled.append("CMP")
        if report.sector is None and info.get("sector"):
            report.sector = info["sector"]
            filled.append("sector")

        # Company-data sidebar (absolute rupees -> Rs. crore where applicable).
        mcap = info.get("marketCap")
        _set_if_none(cd, "market_cap", round(mcap / _CR, 1) if mcap else None)
        ev = info.get("enterpriseValue")
        _set_if_none(cd, "enterprise_value", round(ev / _CR, 1) if ev else None)
        shares = info.get("sharesOutstanding")
        _set_if_none(cd, "outstanding_shares", round(shares / _CR, 2) if shares else None)
        _set_if_none(cd, "week52_high", info.get("fiftyTwoWeekHigh"))
        _set_if_none(cd, "week52_low", info.get("fiftyTwoWeekLow"))
        _set_if_none(cd, "beta", info.get("beta"))
        _set_if_none(cd, "dividend_yield_pct", _dividend_yield_pct(info))

        # Free float % = floatShares / sharesOutstanding.
        float_shares = info.get("floatShares")
        if float_shares and shares:
            _set_if_none(cd, "free_float_pct", round(float(float_shares) / float(shares) * 100.0, 1))

        vol = (info.get("averageVolume") or info.get("averageDailyVolume3Month")
               or info.get("averageDailyVolume10Day"))
        _set_if_none(cd, "avg_volume_6m", round(vol / _CR, 2) if vol else None)

        # Bloomberg-style code for the header meta row (e.g. "ICICIBANK:IN").
        if report.bloomberg_code is None and report.nse_code:
            report.bloomberg_code = f"{report.nse_code.strip()}:IN"

        filled += [f for f in ("market_cap", "enterprise_value", "outstanding_shares",
                               "week52_high", "week52_low", "beta",
                               "dividend_yield_pct", "free_float_pct", "avg_volume_6m")
                   if getattr(cd, f, None) is not None]
    except Exception as exc:
        # A single-field surprise shouldn't lose the fields already set.
        _log(f"partial failure filling company data ({type(exc).__name__}: {str(exc)[:100]})")

    # Benchmark level for the header "Sensex" cell (^BSESN, matching the label).
    try:
        if report.sensex is None:
            import yfinance as yf
            bse = yf.Ticker("^BSESN").history(period="5d")
            if bse is not None and not bse.empty and "Close" in bse:
                closes = bse["Close"].dropna()
                if not closes.empty:
                    report.sensex = round(float(closes.iloc[-1]), 2)
                    filled.append("sensex")
    except Exception as exc:
        _log(f"sensex lookup skipped ({type(exc).__name__})")

    # Price charts — only build when the deck didn't provide its own series.
    try:
        if report.price_1y is None:
            report.price_1y = _price_history(ticker, "1y", max_points=26)
            if report.price_1y:
                filled.append("price_1y")
        if report.price_3y is None:
            report.price_3y = _price_history(ticker, "3y", max_points=36)
            if report.price_3y:
                filled.append("price_3y")
    except Exception as exc:
        _log(f"price charts skipped ({type(exc).__name__}: {str(exc)[:100]})")

    _log(f"filled {len(filled)} field(s): {', '.join(filled) if filled else 'none'}")
    return report
