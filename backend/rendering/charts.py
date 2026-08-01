"""Chart generation matching the Geojit teal/orange combo-chart style.

Each chart is a teal bar series (absolute values) with an orange line series
(growth % or margin %) on a secondary axis, data labels on the line points,
exported as a base64 PNG for inline embedding in the HTML template.
"""
from __future__ import annotations

import base64
import io
import textwrap
from typing import List, Optional

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from models.schema import (  # noqa: E402
    CapacityRow,
    ChartSeries,
    EntityFinancialRow,
    PriceHistory,
)

TEAL = "#0d9488"
TEAL_BAR = "#1aa89a"
TEAL_LINE = "#0d8b7f"
GREY_LINE = "#9aa5b1"
ORANGE = "#f28c28"
ORANGE_SOFT = "#f6b26b"
GREY_BAR = "#c2cbd4"
GRID = "#e5e7eb"

# Chart typography. Every chart is scaled to a fixed column width in the PDF, so
# these sizes translate directly into on-page legibility. They are deliberately
# larger than matplotlib's defaults, which are tuned for on-screen figures.
FS_TICK = 9.0       # axis tick labels
FS_TICK_SM = 8.0    # ticks on wrapped/crowded categorical axes
FS_LABEL = 9.0      # axis titles
FS_LEGEND = 8.5     # legend entries
FS_ANNOT = 8.0      # data labels on the line series


def _fig_to_data_uri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _clean(values):
    return [0.0 if v is None else float(v) for v in values]


def _clean_line(values):
    """Line series: a missing point must break the line, not sit at zero.

    Growth lines have no base for their first period, so plotting None as 0.0
    would draw a fake "0.0%" reading. NaN makes matplotlib skip the point.
    """
    return [float("nan") if v is None else float(v) for v in values]


def _has_data(values) -> bool:
    """True when a series carries at least one real, non-zero reading."""
    return any(v is not None and float(v) != 0.0 for v in values)


def render_combo_chart(series: Optional[ChartSeries]) -> Optional[str]:
    """Return a base64 data-URI PNG for the given series, or None."""
    if series is None or not series.periods:
        return None
    if not _has_data(series.bar_values):
        return None

    periods = series.periods
    bars = _clean(series.bar_values) if series.bar_values else [0] * len(periods)
    line = _clean_line(series.line_values) if series.line_values else None

    fig, ax1 = plt.subplots(figsize=(5.0, 2.35), dpi=150)
    x = range(len(periods))

    ax1.bar(x, bars, width=0.55, color=TEAL_BAR, zorder=2, label=series.bar_legend or "")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(periods, fontsize=FS_TICK, rotation=0)
    ax1.tick_params(axis="y", labelsize=FS_TICK)
    ax1.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax1.grid(axis="y", color=GRID, linewidth=0.7, zorder=0)
    ax1.set_axisbelow(True)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)

    handles, labels = ax1.get_legend_handles_labels()

    if line is not None:
        ax2 = ax1.twinx()
        ax2.plot(x, line, color=ORANGE, linewidth=2.0, marker="", zorder=3,
                 label=series.line_legend or "")
        ax2.tick_params(axis="y", labelsize=FS_TICK)
        for spine in ("top",):
            ax2.spines[spine].set_visible(False)
        if series.line_is_percent:
            ax2.set_ylabel("")
        # data labels on the line (NaN = no data for that period, so no label)
        for xi, yi in zip(x, line):
            if yi != yi:  # NaN
                continue
            ax2.annotate(f"{yi:.1f}%" if series.line_is_percent else f"{yi:.1f}",
                         (xi, yi), textcoords="offset points", xytext=(0, 5),
                         ha="center", fontsize=FS_ANNOT, color="#374151")
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2
        labels += l2

    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=FS_LEGEND,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.07, 1, 1))

    return _fig_to_data_uri(fig)


def render_capacity_chart(capacity: List[CapacityRow]) -> Optional[str]:
    """Stacked horizontal bar chart for capacity profile (installed + U/C + pipeline)."""
    if not capacity:
        return None

    segments = [c.segment for c in capacity]
    installed = [c.installed or 0.0 for c in capacity]
    uc = [c.under_construction or 0.0 for c in capacity]
    pipeline = [c.pipeline or 0.0 for c in capacity]

    # Wrap long segment names
    wrapped = [textwrap.fill(s, width=18) for s in segments]

    fig, ax = plt.subplots(figsize=(5.0, 2.2), dpi=150)
    y = range(len(segments))

    ax.barh(y, installed, color=TEAL_BAR, label="Installed")
    ax.barh(y, uc, left=installed, color=ORANGE, label="Under Construction")
    left_pipe = [i + u for i, u in zip(installed, uc)]
    ax.barh(y, pipeline, left=left_pipe, color=GREY_BAR, label="Pipeline")

    ax.set_yticks(list(y))
    ax.set_yticklabels(wrapped, fontsize=FS_TICK_SM)
    ax.tick_params(axis="x", labelsize=FS_TICK)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.set_xlabel(capacity[0].unit if capacity else "MW", fontsize=FS_LABEL, labelpad=2)
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.legend(loc="upper center", ncol=3, fontsize=FS_LEGEND, frameon=False,
              bbox_to_anchor=(0.5, 1.16))
    fig.tight_layout(rect=(0, 0, 1, 0.90))

    return _fig_to_data_uri(fig)


def render_entity_chart_titled(
    entities: List[EntityFinancialRow],
    current_label: str = "Current Period",
    prior_label: str = "Prior Period",
):
    """(data_uri, measure) where measure is 'Revenue' or 'EBITDA', or None.

    Entity tables aren't always revenue-based — a bank's segment disclosure may
    carry only PBT/EBITDA — so the caller titles the block from the measure
    actually charted rather than assuming revenue.
    """
    return _entity_chart(entities, current_label, prior_label)


def _entity_chart(entities: List[EntityFinancialRow], current_label: str,
                  prior_label: str):
    if not entities:
        return None

    # Entity tables aren't always revenue-based: a bank's segment disclosure may
    # carry only PBT/EBITDA. Chart whichever measure the source actually filled
    # so a heading never renders above an empty plot.
    rev_c = [e.revenue_current for e in entities]
    rev_p = [e.revenue_prior for e in entities]
    ebt_c = [e.ebitda_current for e in entities]
    ebt_p = [e.ebitda_prior for e in entities]

    if _has_data(rev_c) or _has_data(rev_p):
        cur, prior, measure = rev_c, rev_p, "Revenue"
    elif _has_data(ebt_c) or _has_data(ebt_p):
        cur, prior, measure = ebt_c, ebt_p, "EBITDA"
    else:
        return None

    entity_names = [e.entity for e in entities]
    cur_vals = _clean(cur)
    prior_vals = _clean(prior)

    # Wrap long entity names
    wrapped = [textwrap.fill(n, width=16) for n in entity_names]

    fig, ax = plt.subplots(figsize=(5.0, 2.35), dpi=150)
    x = range(len(entity_names))
    width = 0.35

    ax.bar([i - width/2 for i in x], prior_vals, width, color=GREY_BAR, label=prior_label)
    ax.bar([i + width/2 for i in x], cur_vals, width, color=TEAL_BAR, label=current_label)

    ax.set_xticks(list(x))
    ax.set_xticklabels(wrapped, fontsize=FS_TICK_SM, rotation=0)
    ax.tick_params(axis="y", labelsize=FS_TICK)
    ax.set_ylabel(f"{measure} (Rs.cr)", fontsize=FS_LABEL)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.legend(loc="upper center", ncol=2, fontsize=FS_LEGEND, frameon=False,
              bbox_to_anchor=(0.5, 1.14))
    fig.tight_layout(rect=(0, 0, 1, 0.92))

    return _fig_to_data_uri(fig), measure


def render_price_chart(
    hist: Optional[PriceHistory],
    figsize=(5.0, 2.2),
    show_legend: bool = True,
) -> Optional[str]:
    """Stock price vs rebased benchmark line chart (Geojit teal + grey lines)."""
    if hist is None or not hist.labels or not hist.primary:
        return None

    n = len(hist.primary)
    x = range(n)
    fig, ax = plt.subplots(figsize=figsize, dpi=150)

    ax.plot(x, _clean(hist.primary), color=TEAL_LINE, linewidth=1.3, zorder=3,
            label=hist.primary_legend or "")
    if hist.secondary:
        ax.plot(x, _clean(hist.secondary), color=GREY_LINE, linewidth=1.3, zorder=2,
                label=hist.secondary_legend or "")

    # sparse date ticks along the x-axis
    if hist.labels:
        step = max(1, n // (len(hist.labels)))
        tick_pos = list(range(0, n, max(1, n // max(1, len(hist.labels) - 1)))) if len(hist.labels) > 1 else [0]
        tick_pos = tick_pos[: len(hist.labels)]
        while len(tick_pos) < len(hist.labels):
            tick_pos.append(n - 1)
        ax.set_xticks(tick_pos)
        # Date labels sit close together, so they take the smaller tick size.
        ax.set_xticklabels(hist.labels, fontsize=FS_TICK_SM)

    ax.tick_params(axis="y", labelsize=FS_TICK)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    if show_legend and (hist.primary_legend or hist.secondary_legend):
        ax.legend(loc="lower center", ncol=2, fontsize=FS_LEGEND, frameon=False,
                  bbox_to_anchor=(0.5, -0.32))
        fig.tight_layout(rect=(0, 0.08, 1, 1))
    else:
        fig.tight_layout()

    return _fig_to_data_uri(fig)
