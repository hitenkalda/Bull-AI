"""Formatting helpers that turn model values into template-ready strings.

Central place for the None -> "N/A" convention and number formatting so the
template stays declarative.
"""
from __future__ import annotations

from typing import Optional

NA = "N/A"


def fmt_num(v: Optional[float], decimals: int = 0, thousands: bool = True) -> str:
    if v is None:
        return NA
    try:
        f = float(v)
    except (TypeError, ValueError):
        return NA
    if thousands:
        return f"{f:,.{decimals}f}"
    return f"{f:.{decimals}f}"


def fmt_pct(v: Optional[float], decimals: int = 1) -> str:
    if v is None:
        return NA
    return f"{float(v):.{decimals}f}%"


def fmt_growth(v: Optional[float], is_bps: bool = False, decimals: int = 1) -> str:
    """Growth values render as % normally, or as 'bps' for margin rows."""
    if v is None:
        return NA
    if is_bps:
        return f"{float(v):.0f}bps"
    return f"{float(v):.{decimals}f}"


def fmt_str(v: Optional[str]) -> str:
    if v is None or str(v).strip() == "":
        return NA
    return str(v)


def fmt_price(v: Optional[float], decimals: int = 0) -> str:
    if v is None:
        return NA
    return f"Rs. {float(v):,.{decimals}f}"


def build_template_context(report, charts: dict) -> dict:
    """Assemble the Jinja context: the report plus formatting filters + charts."""
    return {
        "r": report,
        "charts": charts,
        "fmt_num": fmt_num,
        "fmt_pct": fmt_pct,
        "fmt_growth": fmt_growth,
        "fmt_str": fmt_str,
        "fmt_price": fmt_price,
        "NA": NA,
    }
