"""A deliberately sparse report used to demonstrate graceful degradation.

Many companies' source decks (e.g. a chart-only investor presentation) won't
contain shareholding tables, full balance sheets, or every ratio. This sample
leaves those fields empty so the template's "N/A" / "-" fallbacks are visible in
a real generated PDF — proving requirement #7 (graceful degradation) end-to-end.
"""
from __future__ import annotations

from models.schema import (
    CapacityRow,
    ChangeInEstimateRow,
    ChartSeries,
    CompanyData,
    CompanyReport,
    EntityFinancialRow,
    MetricRow,
    PricePerformanceRow,
    QuarterlyFinancial,
    RecommendationRow,
    YearlyEstimate,
)

_FIN_YEARS = ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E"]


def _row(*vals):
    return {y: v for y, v in zip(_FIN_YEARS, vals)}


def partial_report(company_name: str = "Pondy Oxides & Chemicals Ltd.") -> CompanyReport:
    """Realistic 'thin deck' extraction: headline metrics present, deep tables absent."""
    return CompanyReport(
        company_name=company_name or "Pondy Oxides & Chemicals Ltd.",
        sector="Non Ferrous Metals",
        report_date="12th November, 2025",
        report_tag="Q2FY26 Result Update",
        rating="BUY",
        target_price=980,
        current_price=812,
        return_pct=21,
        change_target="up",
        change_rating="neutral",
        change_earnings="up",
        stock_type="Small Cap",
        bloomberg_code="POCL:IN",
        sensex=None,                       # not in the deck -> renders N/A
        nse_code="POCL",
        bse_code="532626",
        time_frame="12 Months",
        data_as_of="12-November-2025, 15:10hrs",
        headline="Recycling capacity ramp-up drives volume growth",
        company_overview=(
            "Pondy Oxides & Chemicals Ltd. is one of India's largest lead recyclers, "
            "producing pure lead, lead alloys and plastic additives, primarily serving "
            "the automotive and industrial battery industry."
        ),
        key_highlights_short=[
            "Revenue grew 18.2% YoY in Q2FY26 on higher lead volumes and firm realisations.",
            "EBITDA margin expanded ~90bps YoY to 5.1% as the aluminium alloy line scaled up.",
            "Management guided to commissioning the new recycling capacity by Q4FY26.",
            # Only four bullets available from the deck; page still balances.
        ],
        key_highlights=[
            "The company is expanding into aluminium and plastic recycling to diversify "
            "beyond lead, targeting a more balanced revenue mix over the next two years.",
            "Working capital intensity remains the key monitorable as volumes scale; "
            "management expects the cash conversion cycle to stay within historical bands.",
        ],
        outlook_valuation=(
            "We remain positive on the structural recycling opportunity and the company's "
            "capacity expansion. At the current price the stock trades below its historical "
            "average multiple; we maintain BUY with a target price of Rs. 980."
        ),
        company_data=CompanyData(
            market_cap=4720,
            week52_high=985,
            week52_low=430,
            enterprise_value=5010,
            outstanding_shares=5.8,
            free_float_pct=54.2,
            dividend_yield_pct=0.3,
            avg_volume_6m=0.2,
            beta=0.9,
            face_value=10.0,
        ),
        # Shareholding table absent in this deck -> section is skipped entirely.
        shareholding_pattern=[],
        price_performance=[
            PricePerformanceRow(label="Absolute Return", m3=14.0, m6=28.5, y1=61.2),
            PricePerformanceRow(label="Absolute Sensex", m3=2.1, m6=6.4, y1=9.8),
            PricePerformanceRow(label="Relative Return", m3=11.9, m6=22.1, y1=51.4),
        ],
        yearly_estimates=[
            YearlyEstimate(year="FY25A", sales=3120, sales_growth_pct=12.4, ebitda=142,
                           ebitda_margin_pct=4.5, pat_adjusted=88, pat_growth_pct=18.0,
                           adjusted_eps=15.2, eps_growth_pct=18.0, pe=17.8, pb=2.6,
                           ev_ebitda=9.1, roe_pct=15.4, de=0.5),
            YearlyEstimate(year="FY26E", sales=3690, sales_growth_pct=18.3, ebitda=188,
                           ebitda_margin_pct=5.1, pat_adjusted=120, pat_growth_pct=36.4,
                           adjusted_eps=20.7, eps_growth_pct=36.4, pe=13.1, pb=2.2,
                           ev_ebitda=7.2, roe_pct=17.9, de=0.4),
            # FY27E column intentionally omitted from the deck.
        ],
        quarterly_financials=[
            QuarterlyFinancial(metric="Sales", current_q=942, year_ago_q=797, yoy_growth=18.2, prev_q=889, qoq_growth=6.0),
            QuarterlyFinancial(metric="EBITDA", current_q=48, year_ago_q=33, yoy_growth=45.5, prev_q=42, qoq_growth=14.3),
            QuarterlyFinancial(metric="Margin (%)", current_q=5.1, year_ago_q=4.2, yoy_growth=90, prev_q=4.7, qoq_growth=40, is_bps=True),
            # EBIT / PBT / PAT rows not disclosed this quarter -> render N/A.
            QuarterlyFinancial(metric="Rep. PAT", current_q=31, year_ago_q=None, yoy_growth=None, prev_q=27, qoq_growth=14.8),
            QuarterlyFinancial(metric="Adj. EPS (Rs)", current_q=5.3, year_ago_q=None, yoy_growth=None, prev_q=4.6, qoq_growth=15.2),
        ],
        # No change-in-estimates table in the deck.
        change_in_estimates=[],
        revenue_chart=ChartSeries(
            label="Revenue", periods=["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25", "Q1FY26", "Q2FY26"],
            bar_values=[760, 797, 812, 838, 889, 942],
            line_values=[4.1, 4.9, 1.9, 3.2, 6.1, 6.0],
            bar_legend="Revenue (Rs.cr)", line_legend="Growth (QoQ)",
        ),
        ebitda_chart=ChartSeries(
            label="EBITDA", periods=["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25", "Q1FY26", "Q2FY26"],
            bar_values=[30, 33, 35, 38, 42, 48],
            line_values=[3.9, 4.2, 4.3, 4.5, 4.7, 5.1],
            bar_legend="EBITDA (Rs.cr)", line_legend="Margin",
        ),
        # GOV and PAT charts not applicable / not in deck -> omitted (grid reflows).
        gov_chart=None,
        pat_chart=None,
        financial_years=_FIN_YEARS,
        # Only a partial P&L was disclosed; balance sheet / cashflow / ratios absent.
        profit_loss={
            "Sales": _row(2470, 2776, 3120, 3690, None),
            "% change": _row(None, 12.4, 12.4, 18.3, None),
            "EBITDA": _row(96, 118, 142, 188, None),
            "EBIT": _row(78, 96, 118, 158, None),
            "PBT": _row(64, 80, 101, 140, None),
            "Reported PAT": _row(48, 62, 88, 120, None),
            "Adj EPS (Rs.)": _row(8.3, 10.7, 15.2, 20.7, None),
        },
        balance_sheet={},
        cashflow={},
        ratios={
            "EBITDA margin (%)": _row(3.9, 4.3, 4.5, 5.1, None),
            "ROE (%)": _row(12.1, 13.8, 15.4, 17.9, None),
            "P/E (x)": _row(None, None, 17.8, 13.1, None),
        },
        recommendation_history=[
            RecommendationRow(date="10-Nov-24", rating="BUY", target=520),
            RecommendationRow(date="14-May-25", rating="BUY", target=760),
            RecommendationRow(date="12-Nov-25", rating="BUY", target=980),
        ],
        # No price-history series provided in this deck.
        price_1y=None,
        price_3y=None,
        q_current_label="Q2FY26",
        q_year_ago_label="Q2FY25",
        q_prev_label="Q1FY26",
        # --- Deck-grounded extras (showcase the new result-presentation sections) ---
        operational_metrics=[
            MetricRow(label="Lead volumes", value="42,300 MT", change="+16.8% YoY"),
            MetricRow(label="Capacity utilisation", value="86%", change="+540 bps YoY"),
            MetricRow(label="Aluminium alloy share", value="18% of revenue", change="+700 bps YoY"),
            MetricRow(label="Receivable days (DSO)", value="38 days", change="-4 days YoY"),
            MetricRow(label="Cash & equivalents", value="Rs.212 cr", change=None),
            MetricRow(label="Net debt / equity", value="0.4x", change="-0.1x YoY"),
            MetricRow(label="Credit rating", value="A/Stable/A1", change="Reaffirmed"),
        ],
        capacity_profile=[
            CapacityRow(segment="Lead recycling", installed=132000, under_construction=48000, pipeline=None, unit="MTPA"),
            CapacityRow(segment="Aluminium alloys", installed=24000, under_construction=12000, pipeline=18000, unit="MTPA"),
            CapacityRow(segment="Plastic additives", installed=9000, under_construction=None, pipeline=None, unit="MTPA"),
        ],
        entity_financials=[
            EntityFinancialRow(entity="POCL (standalone)", revenue_current=812, revenue_prior=705, ebitda_current=39, ebitda_prior=27),
            EntityFinancialRow(entity="Lohat Recycling (sub.)", revenue_current=118, revenue_prior=84, ebitda_current=7, ebitda_prior=5),
            EntityFinancialRow(entity="POCL Global (JV)", revenue_current=12, revenue_prior=8, ebitda_current=2, ebitda_prior=1),
        ],
        entity_period_current="Q2FY26",
        entity_period_prior="Q2FY25",
        guidance=[
            "Commission the new 48,000 MTPA lead recycling line by Q4FY26.",
            "Scale aluminium alloys to ~25% of revenue over FY26-FY27.",
            "Hold net debt/equity below 0.5x through the expansion phase.",
        ],
        investment_rationale=[
            "Volume-led growth: lead throughput up 16.8% YoY with utilisation at 86%.",
            "Margin expansion as the higher-value aluminium alloy line scales.",
            "Diversification beyond lead reduces single-commodity price exposure.",
            "Balance sheet remains comfortable (net D/E 0.4x) to fund the capacity ramp.",
        ],
        key_concerns=[
            "Lead price volatility can compress spreads within a quarter.",
            "Working-capital intensity rises as volumes and new lines scale.",
            "Execution risk on the Q4FY26 recycling-line commissioning timeline.",
            "Regulatory/environmental compliance costs for recycling operations.",
        ],
    )
