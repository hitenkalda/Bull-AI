"""Fixed report schema (Pydantic v2, Python 3.9 compatible).

Every numeric field is Optional[float] / Optional[str]; missing values arrive as
``None`` and are rendered as "N/A" downstream. This single convention is the app's
graceful-degradation mechanism — the template never crashes on missing data.

The schema mirrors the Geojit "Result Update" layout so the generated PDF can
reproduce it field-for-field:
  * Page 1 — header/rating, company data, shareholding, price performance,
             overview, key highlights, outlook, yearly estimates, quarterly financials
  * Page 2 — key highlights, charts (revenue/GOV/EBITDA/PAT), change in estimates
  * Page 3 — consolidated financials: P&L, balance sheet, cashflow, ratios
  * Page 4 — recommendation history (static disclaimer lives in the template)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Page 1 — sidebar blocks
# --------------------------------------------------------------------------- #
class CompanyData(BaseModel):
    market_cap: Optional[float] = None          # Rs. cr
    week52_high: Optional[float] = None
    week52_low: Optional[float] = None
    enterprise_value: Optional[float] = None     # Rs. cr
    outstanding_shares: Optional[float] = None   # cr
    free_float_pct: Optional[float] = None
    dividend_yield_pct: Optional[float] = None
    avg_volume_6m: Optional[float] = None        # cr
    beta: Optional[float] = None
    face_value: Optional[float] = None


class ShareholdingRow(BaseModel):
    period: str
    promoters_pct: Optional[float] = None
    fii_pct: Optional[float] = None
    institutions_pct: Optional[float] = None      # MFs / DIIs
    public_pct: Optional[float] = None
    others_pct: Optional[float] = None
    total_pct: Optional[float] = None
    promoter_pledge: Optional[str] = None         # usually "Nil"


class PricePerformanceRow(BaseModel):
    label: str                                    # Absolute Return / Absolute Sensex / Relative Return
    m3: Optional[float] = None
    m6: Optional[float] = None
    y1: Optional[float] = None


# --------------------------------------------------------------------------- #
# Page 1 / 2 — estimate & financial tables
# --------------------------------------------------------------------------- #
class YearlyEstimate(BaseModel):
    year: str                                     # FY25A / FY26E / FY27E
    sales: Optional[float] = None
    sales_growth_pct: Optional[float] = None
    ebitda: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    pat_adjusted: Optional[float] = None
    pat_growth_pct: Optional[float] = None
    adjusted_eps: Optional[float] = None
    eps_growth_pct: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    ev_ebitda: Optional[float] = None
    roe_pct: Optional[float] = None
    de: Optional[float] = None


class QuarterlyFinancial(BaseModel):
    """One metric row of the quarterly comparison table."""
    metric: str                                   # Sales / EBITDA / Margin (%) / EBIT / PBT / Rep. PAT / Adj PAT / Adj. EPS (Rs)
    current_q: Optional[float] = None             # Q1FY26
    year_ago_q: Optional[float] = None            # Q1FY25
    yoy_growth: Optional[float] = None            # % (or bps for margin)
    prev_q: Optional[float] = None                # Q4FY25
    qoq_growth: Optional[float] = None            # % (or bps for margin)
    is_bps: bool = False                          # render growth as "bps" not "%"


class ChangeInEstimateRow(BaseModel):
    label: str                                    # Revenue / EBITDA / Margins (%) / Adj. PAT / EPS
    old_fy26: Optional[float] = None
    old_fy27: Optional[float] = None
    new_fy26: Optional[float] = None
    new_fy27: Optional[float] = None
    change_fy26: Optional[float] = None
    change_fy27: Optional[float] = None
    is_bps: bool = False


# --------------------------------------------------------------------------- #
# Deck-grounded content (results-presentation extras)
#
# A company's own results deck carries structured content a broker note omits:
# operational KPIs, a capacity roadmap, entity-wise financials, guidance, and
# the analyst read of it (rationale / concerns). These populate the areas the
# template leaves blank when broker-only blocks (shareholding, price perf,
# estimates, CIE, reco history) are absent. All Optional / default-empty, so a
# report without them (e.g. the Eternal broker-note example) renders unchanged.
# --------------------------------------------------------------------------- #
class MetricRow(BaseModel):
    """One operational KPI. value is a string to hold non-numeric readings
    like 'AA/Stable/A1+', '64 days', '14.9 BUs'."""
    label: str
    value: Optional[str] = None
    change: Optional[str] = None                   # YoY change string when stated


class CapacityRow(BaseModel):
    """One row of the capacity roadmap / segment mix."""
    segment: str                                   # Thermal / Renewable / Total
    installed: Optional[float] = None
    under_construction: Optional[float] = None
    pipeline: Optional[float] = None
    unit: Optional[str] = "MW"


class EntityFinancialRow(BaseModel):
    """Entity-wise revenue & EBITDA for two comparable periods."""
    entity: str
    revenue_current: Optional[float] = None
    revenue_prior: Optional[float] = None
    ebitda_current: Optional[float] = None
    ebitda_prior: Optional[float] = None


class ChartSeries(BaseModel):
    label: str
    periods: List[str] = Field(default_factory=list)
    bar_values: List[Optional[float]] = Field(default_factory=list)      # bars (Rs.cr / Rs.bn)
    line_values: List[Optional[float]] = Field(default_factory=list)     # line (growth % / margin %)
    bar_legend: str = ""
    line_legend: str = ""
    line_is_percent: bool = True


class RecommendationRow(BaseModel):
    date: str
    rating: Optional[str] = None
    target: Optional[float] = None


class PriceHistory(BaseModel):
    """Price line chart: stock vs rebased benchmark over time."""
    labels: List[str] = Field(default_factory=list)
    primary: List[Optional[float]] = Field(default_factory=list)     # stock price
    secondary: List[Optional[float]] = Field(default_factory=list)   # benchmark (rebased)
    primary_legend: str = ""
    secondary_legend: str = ""


# --------------------------------------------------------------------------- #
# Top-level report
# --------------------------------------------------------------------------- #
class CompanyReport(BaseModel):
    # Header / rating block
    company_name: str
    sector: Optional[str] = None
    report_date: Optional[str] = None
    report_tag: Optional[str] = "Result Update"
    rating: Optional[str] = None                  # HOLD / BUY / ...
    target_price: Optional[float] = None
    current_price: Optional[float] = None          # CMP
    return_pct: Optional[float] = None
    # Key changes arrows (up / down / neutral)
    change_target: Optional[str] = None            # "up" | "down" | "neutral"
    change_rating: Optional[str] = None
    change_earnings: Optional[str] = None
    # Stock meta row
    stock_type: Optional[str] = None               # Large Cap
    bloomberg_code: Optional[str] = None
    sensex: Optional[float] = None
    nse_code: Optional[str] = None
    bse_code: Optional[str] = None
    time_frame: Optional[str] = None               # 12 Months
    data_as_of: Optional[str] = None

    # Narrative
    headline: Optional[str] = None                 # "Blinkit propels growth; valuation limits upside"
    company_overview: Optional[str] = None
    key_highlights_short: List[str] = Field(default_factory=list)   # page-1 bullets
    key_highlights: List[str] = Field(default_factory=list)         # page-2 detailed bullets
    outlook_valuation: Optional[str] = None

    # Sidebar blocks
    company_data: CompanyData = Field(default_factory=CompanyData)
    shareholding_pattern: List[ShareholdingRow] = Field(default_factory=list)
    price_performance: List[PricePerformanceRow] = Field(default_factory=list)

    # Tables
    yearly_estimates: List[YearlyEstimate] = Field(default_factory=list)
    quarterly_financials: List[QuarterlyFinancial] = Field(default_factory=list)
    # Column headers for the quarterly comparison table (default = Eternal Q1FY26 layout)
    q_current_label: Optional[str] = "Q1FY26"
    q_year_ago_label: Optional[str] = "Q1FY25"
    q_prev_label: Optional[str] = "Q4FY25"
    change_in_estimates: List[ChangeInEstimateRow] = Field(default_factory=list)

    # Charts
    revenue_chart: Optional[ChartSeries] = None
    gov_chart: Optional[ChartSeries] = None
    ebitda_chart: Optional[ChartSeries] = None
    pat_chart: Optional[ChartSeries] = None

    # Consolidated financials (page 3) — ordered dicts: metric -> {year -> value}
    profit_loss: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    balance_sheet: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    cashflow: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    ratios: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    financial_years: List[str] = Field(default_factory=list)   # column headers for page-3 tables

    # Page 4
    recommendation_history: List[RecommendationRow] = Field(default_factory=list)

    # Price charts (page 1: 1-year; page 4: 3-year)
    price_1y: Optional[PriceHistory] = None
    price_3y: Optional[PriceHistory] = None

    # Deck-grounded content (results presentation extras)
    operational_metrics: List[MetricRow] = Field(default_factory=list)
    capacity_profile: List[CapacityRow] = Field(default_factory=list)
    entity_financials: List[EntityFinancialRow] = Field(default_factory=list)
    entity_period_current: Optional[str] = "Q2FY26"
    entity_period_prior: Optional[str] = "Q2FY25"
    guidance: List[str] = Field(default_factory=list)
    investment_rationale: List[str] = Field(default_factory=list)
    key_concerns: List[str] = Field(default_factory=list)
