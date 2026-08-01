"""Deterministic mock extraction.

Used when GEMINI_API_KEY is absent so the full pipeline (and the example PDFs)
work without network access. The payload mirrors the Geojit "Eternal Ltd."
reference report field-for-field, which doubles as a fidelity golden sample.
"""
from __future__ import annotations

import math

from models.schema import (
    ChangeInEstimateRow,
    ChartSeries,
    CompanyData,
    CompanyReport,
    PriceHistory,
    PricePerformanceRow,
    QuarterlyFinancial,
    RecommendationRow,
    ShareholdingRow,
    YearlyEstimate,
)

_QUARTERS = ["Q2FY24", "Q3FY24", "Q4FY24", "Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25", "Q1FY26"]


def _price_series(n, start, end, amp, waves, phase=0.0):
    """Deterministic price-like curve: trend + damped sine wobble (no RNG)."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        trend = start + (end - start) * (t ** 1.15)
        wobble = amp * math.sin(waves * math.pi * t + phase) * (0.55 + 0.45 * t)
        out.append(round(trend + wobble, 1))
    return out


def _price_1y():
    n = 52
    labels = ["Jul-24", "Oct-24", "Jan-25", "Apr-25", "Jul-25"]
    stock = _price_series(n, 205, 300, 16, 5, 0.4)
    stock[-1] = 306.0
    bench = _price_series(n, 205, 232, 7, 4, 1.1)
    return PriceHistory(labels=labels, primary=stock, secondary=bench,
                        primary_legend="ETERNAL", secondary_legend="Sensex Rebased")


def _price_3y():
    n = 156
    labels = ["Jul-22", "Jan-23", "Jul-23", "Jan-24", "Jul-24", "Jan-25", "Jul-25"]
    stock = _price_series(n, 48, 300, 22, 7, 0.2)
    stock[-1] = 306.0
    return PriceHistory(labels=labels, primary=stock, primary_legend="ETERNAL")


def _fin_years():
    return ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E"]


def _row(*vals):
    """Build a {year: value} dict aligned to financial_years order."""
    ys = _fin_years()
    return {y: v for y, v in zip(ys, vals)}


def mock_report(company_name: str = "Eternal Ltd.") -> CompanyReport:
    fy = _fin_years()
    return CompanyReport(
        company_name=company_name or "Eternal Ltd.",
        sector="Internet & Catalogue Retail",
        report_date="29th July, 2025",
        report_tag="Q1FY26 Result Update",
        rating="HOLD",
        target_price=337,
        current_price=306,
        return_pct=10,
        change_target="up",
        change_rating="down",
        change_earnings="down",
        stock_type="Large Cap",
        bloomberg_code="ETERNAL:IN",
        sensex=81334,
        nse_code="ETERNAL",
        bse_code="543320",
        time_frame="12 Months",
        data_as_of="29-July-2025, 16:23hrs",
        headline="Blinkit propels growth; valuation limits upside",
        company_overview=(
            "Eternal Limited, formerly Zomato Limited, operates as an online food delivery "
            "company. It runs a B2C platform under the Zomato brand. The company also operates "
            "Hyperpure and Blinkit, organises events, provides payment services and engages in "
            "investment activities."
        ),
        key_highlights_short=[
            "Consolidated revenue from operations surged 70.4% YoY in Q1FY26 to Rs. 7,167cr "
            "as all segments demonstrated robust growth.",
            "Revenue from the quick commerce business soared 154.8% YoY to Rs. 2,400cr, while "
            "the Hyperpure supplies and India food ordering and delivery segment grew 89.4% "
            "and 16.4% YoY, respectively.",
            "Net order value (NOV) of B2C businesses rose 55% YoY to Rs. 20,183cr in Q1FY26, "
            "with quick commerce NOV exceeding food delivery NOV for the first time.",
            "EBITDA fell 35.0% YoY to Rs. 115cr in Q1FY26, mainly due to higher operating "
            "expenses; consequently EBITDA margin declined 260bps to 1.6%.",
            "Reported PAT plunged 90.1% YoY to Rs. 25cr in Q1FY26 because of lower EBITDA.",
            "Blinkit added 243 new stores in Q1FY26, taking the total to 1,544 stores, and "
            "aims to hit 2,000 stores by December 2025.",
        ],
        key_highlights=[
            "NOV growth in food delivery edged lower to 13% YoY in Q1FY26 from 14% in the "
            "previous quarter. The growth trajectory of NOV is expected to stabilise after "
            "seeing a downturn in late 2024. For FY26, a growth rate exceeding 15% is "
            "anticipated, with a potential upward trend towards 20% in FY27.",
            "Margins of the food delivery business declined QoQ despite expanding YoY, due to "
            "lower availability of delivery partners on account of festivals and adverse "
            "weather conditions, which is a seasonal impact that occurs every year in Q1.",
            "The long-term profitability of the Blinkit business is not a concern, as a "
            "significant portion of the business is already generating profits, with certain "
            "cities achieving an impressive 2.5%+ adjusted EBITDA margin (as a percentage of "
            "NOV). The early achievement of such margin is a strong indication of the "
            "feasibility of the company's long-term guidance of a 5-6% margin.",
            "The Blinkit business witnessed a remarkable 127% YoY growth in NOV, driven by a "
            "significant 123% increase in average monthly transacting customers. The company's "
            "profitability also improved, despite ongoing investments in new store roll-outs "
            "and seasonal factors.",
            "The company is transitioning its quick commerce business from a marketplace model "
            "to inventory ownership over the next 2-3 quarters, anticipating a 1 percentage "
            "point margin expansion as a result, while also expecting shrinkage in Hyperpure's "
            "non-restaurant business as most B2B buyers in Hyperpure's non-restaurant business "
            "were sellers on the quick commerce platform.",
        ],
        outlook_valuation=(
            "Eternal Limited is poised for long-term growth and improved profitability, driven "
            "by its strong market position and growth prospects in the quick commerce business "
            "(QCB). The company's focus on inventory ownership and margin improvement is "
            "expected to drive profitability. Although the industry outlook remains competitive, "
            "the company's strategy and long-term growth objectives, along with its strong "
            "management team, are expected to drive future growth. However, the stock's "
            "significant run-up in price and rich valuations limit the upside potential from "
            "current levels. Therefore, we downgrade our rating on the stock to HOLD from BUY "
            "with a revised target price of Rs. 337, based on 6x FY27 price/sales."
        ),
        company_data=CompanyData(
            market_cap=295735,
            week52_high=314,
            week52_low=190,
            enterprise_value=294166,
            outstanding_shares=965.0,
            free_float_pct=71.9,
            dividend_yield_pct=None,
            avg_volume_6m=6.1,
            beta=1.0,
            face_value=1.0,
        ),
        shareholding_pattern=[
            ShareholdingRow(period="Q3FY25", promoters_pct=0.0, fii_pct=47.3, institutions_pct=20.5,
                            public_pct=8.0, others_pct=24.1, total_pct=100.0, promoter_pledge="Nil"),
            ShareholdingRow(period="Q4FY25", promoters_pct=0.0, fii_pct=44.4, institutions_pct=23.6,
                            public_pct=8.5, others_pct=23.6, total_pct=100.0, promoter_pledge="Nil"),
            ShareholdingRow(period="Q1FY26", promoters_pct=0.0, fii_pct=42.3, institutions_pct=26.6,
                            public_pct=7.6, others_pct=23.5, total_pct=100.0, promoter_pledge="Nil"),
        ],
        price_performance=[
            PricePerformanceRow(label="Absolute Return", m3=32.1, m6=44.8, y1=39.7),
            PricePerformanceRow(label="Absolute Sensex", m3=3.0, m6=7.9, y1=2.5),
            PricePerformanceRow(label="Relative Return", m3=29.2, m6=36.9, y1=37.1),
        ],
        yearly_estimates=[
            YearlyEstimate(year="FY25A", sales=20243, sales_growth_pct=67.1, ebitda=637,
                           ebitda_margin_pct=3.1, pat_adjusted=527, pat_growth_pct=50.1,
                           adjusted_eps=0.6, eps_growth_pct=46.3, pe=335.8, pb=6.4,
                           ev_ebitda=302.2, roe_pct=1.7, de=0.1),
            YearlyEstimate(year="FY26E", sales=35020, sales_growth_pct=73.0, ebitda=1248,
                           ebitda_margin_pct=3.6, pat_adjusted=927, pat_growth_pct=75.9,
                           adjusted_eps=1.0, eps_growth_pct=60.1, pe=325.2, pb=9.6,
                           ev_ebitda=240.3, roe_pct=3.0, de=0.1),
            YearlyEstimate(year="FY27E", sales=54632, sales_growth_pct=56.0, ebitda=3575,
                           ebitda_margin_pct=6.5, pat_adjusted=2643, pat_growth_pct=185.2,
                           adjusted_eps=2.7, eps_growth_pct=185.2, pe=114.1, pb=8.9,
                           ev_ebitda=84.0, roe_pct=7.8, de=0.1),
        ],
        quarterly_financials=[
            QuarterlyFinancial(metric="Sales", current_q=7167, year_ago_q=4206, yoy_growth=70.4, prev_q=5833, qoq_growth=22.9),
            QuarterlyFinancial(metric="EBITDA", current_q=115, year_ago_q=177, yoy_growth=-35.0, prev_q=72, qoq_growth=59.7),
            QuarterlyFinancial(metric="Margin (%)", current_q=1.6, year_ago_q=4.2, yoy_growth=-260, prev_q=1.2, qoq_growth=40, is_bps=True),
            QuarterlyFinancial(metric="EBIT", current_q=-199, year_ago_q=28, yoy_growth=-810.7, prev_q=-215, qoq_growth=7.4),
            QuarterlyFinancial(metric="PBT", current_q=88, year_ago_q=239, yoy_growth=-63.2, prev_q=97, qoq_growth=-9.3),
            QuarterlyFinancial(metric="Rep. PAT", current_q=25, year_ago_q=253, yoy_growth=-90.1, prev_q=39, qoq_growth=-35.9),
            QuarterlyFinancial(metric="Adj PAT", current_q=25, year_ago_q=253, yoy_growth=-90.1, prev_q=39, qoq_growth=-35.9),
            QuarterlyFinancial(metric="Adj. EPS (Rs)", current_q=0.03, year_ago_q=0.3, yoy_growth=-90.1, prev_q=0.04, qoq_growth=-35.9),
        ],
        change_in_estimates=[
            ChangeInEstimateRow(label="Revenue", old_fy26=30738, old_fy27=41743, new_fy26=35020, new_fy27=54632, change_fy26=13.9, change_fy27=30.9),
            ChangeInEstimateRow(label="EBITDA", old_fy26=1686, old_fy27=3959, new_fy26=1248, new_fy27=3575, change_fy26=-25.9, change_fy27=-9.7),
            ChangeInEstimateRow(label="Margins (%)", old_fy26=5.5, old_fy27=9.5, new_fy26=3.6, new_fy27=6.5, change_fy26=-190, change_fy27=-300, is_bps=True),
            ChangeInEstimateRow(label="Adj. PAT", old_fy26=1460, old_fy27=3254, new_fy26=927, new_fy27=2643, change_fy26=-36.5, change_fy27=-18.8),
            ChangeInEstimateRow(label="EPS", old_fy26=1.6, old_fy27=3.6, new_fy26=1.0, new_fy27=2.7, change_fy26=-40.4, change_fy27=-23.7),
        ],
        revenue_chart=ChartSeries(
            label="Revenue", periods=_QUARTERS,
            bar_values=[2848, 3288, 3562, 4206, 5003, 5405, 5833, 7167],
            line_values=[17.9, 15.4, 8.3, 18.1, 14.1, 12.6, 7.9, 22.9],
            bar_legend="Revenue (Rs.cr)", line_legend="Growth (QoQ)",
        ),
        gov_chart=ChartSeries(
            label="Gross Order Value", periods=_QUARTERS,
            bar_values=[113, 132, 139, 158, 178, 203, 213, 249],
            line_values=[13.4, 12.8, 5.0, 14.2, 14.3, 14.4, 5.8, 16.7],
            bar_legend="GOV (Rs. Bn)", line_legend="Growth (QoQ)",
        ),
        ebitda_chart=ChartSeries(
            label="EBITDA", periods=_QUARTERS,
            bar_values=[-45, 55, 95, 178, 225, 165, 72, 115],
            line_values=[-1.7, 1.6, 2.4, 4.2, 4.7, 3.0, 1.2, 1.6],
            bar_legend="EBITDA (Rs.cr)", line_legend="Margin",
        ),
        pat_chart=ChartSeries(
            label="PAT", periods=_QUARTERS,
            bar_values=[36, 138, 175, 253, 176, 103, 39, 25],
            line_values=[1.3, 4.2, 4.9, 6.0, 3.7, 1.1, 0.7, 0.3],
            bar_legend="PAT (Rs.cr)", line_legend="Margin",
        ),
        financial_years=fy,
        profit_loss={
            "Sales": _row(7079, 12114, 20243, 35020, 54632),
            "% change": _row(68.9, 71.1, 67.1, 73.0, 56.0),
            "EBITDA": _row(-1210, 42, 637, 1248, 3575),
            "% change ": _row(-35.4, -100.1, 63600.0, 96.0, 186.3),
            "Depreciation": _row(437, 526, 863, 1233, 1372),
            "EBIT": _row(-1647, -484, -226, 16, 2203),
            "Interest": _row(49, 72, 154, 181, 208),
            "Other Income": _row(681, 847, 1077, 1401, 1530),
            "PBT": _row(-1015, 291, 697, 1236, 3524),
            "% change  ": _row(-16.8, -128.7, 139.5, 77.3, 185.2),
            "Tax": _row(44, 60, -170, 309, 881),
            "Tax Rate (%)": _row(-4.3, 20.6, -24.4, 25.0, 25.0),
            "Reported PAT": _row(-971, 351, 527, 927, 2643),
            "PAT att. to common shareholders": _row(-971, 351, 527, 927, 2643),
            "Adj.*": _row(None, None, None, None, None),
            "Adj. PAT": _row(-971, 351, 527, 927, 2643),
            "% change   ": _row(-35.5, -136.1, 50.1, 75.9, 185.2),
            "No. of shares (cr)": _row(855.4, 882.0, 965.0, 965.0, 965.0),
            "Adj EPS (Rs.)": _row(-1.2, 0.4, 0.6, 1.0, 2.7),
            "% change    ": _row(-28.1, -134.2, 46.3, 60.1, 185.2),
            "DPS (Rs.)": _row(None, None, None, None, None),
        },
        balance_sheet={
            "Cash": _row(1017, 731, 3614, 3203, 3155),
            "Accts. Receivable": _row(457, 794, 1946, 3309, 4971),
            "Inventories": _row(83, 88, 176, 350, 511),
            "Other Cur. Assets": _row(9274, 3845, 5965, 6227, 6566),
            "Investments": _row(2280, 10365, 10920, 12012, 13814),
            "Gross Fixed Assets": _row(363, 529, 1460, 2511, 3740),
            "Net Fixed Assets": _row(636, 977, 2883, 3063, 3198),
            "CWIP": _row(7, 18, 51, 56, 62),
            "Intangible Assets": _row(5708, 5471, 6649, 6569, 6888),
            "Def. Tax -Net": _row(None, None, None, None, None),
            "Other Assets": _row(2137, 1067, 3419, 3556, 3700),
            "Total Assets": _row(21599, 23356, 35623, 38346, 42866),
            "Current Liabilities": _row(1406, 2083, 3326, 5022, 6791),
            "Provisions": _row(94, 88, 120, 138, 159),
            "Debt Funds": _row(392, 588, 1654, 1737, 1824),
            "Other Liabilities": _row(254, 191, 213, 213, 213),
            "Equity Capital": _row(836, 868, 907, 907, 907),
            "Res. & Surplus": _row(18624, 19545, 29410, 30337, 32980),
            "Shareholder Funds": _row(19460, 20413, 30317, 31244, 33887),
            "Minority Interest": _row(-7, -7, -7, -7, -7),
            "Total Liabilities": _row(21599, 23356, 35623, 38346, 42866),
            "BVPS": _row(23, 23, 31, 32, 35),
        },
        cashflow={
            "Net inc. + Depn.": _row(-520, 836, 1390, 2160, 4015),
            "Non-cash adj.": _row(-7, -48, -506, -1803, -2925),
            "Other adjustments": _row(None, None, None, None, None),
            "Changes in W.C": _row(-317, -142, -576, 89, -134),
            "C.F. Operation": _row(-844, 646, 308, 445, 956),
            "Capital exp.": _row(-101, -202, -931, -1051, -1229),
            "Change in inv.": _row(179, 4073, -5941, -68, -70),
            "Other invest.CF": _row(379, -4218, -1121, 181, 208),
            "C.F - Investment": _row(457, -347, -7993, -938, -1091),
            "Issue of equity": _row(4, 23, 8501, None, None),
            "Issue/repay debt": _row(-23, -40, None, 83, 87),
            "Dividends paid": _row(None, None, None, None, None),
            "Other finance.CF": _row(-108, -190, -459, None, None),
            "C.F - Finance": _row(-127, -207, 8042, 83, 87),
            "Chg. in cash": _row(-514, 92, 357, -411, -48),
            "Closing Cash": _row(1017, 731, 3614, 3203, 3155),
        },
        ratios={
            "EBITDA margin (%)": _row(-17.1, 0.3, 3.1, 3.6, 6.5),
            "EBIT margin (%)": _row(-23.3, -4.0, -1.1, 0.0, 4.0),
            "Net profit mgn.(%)": _row(-13.7, 2.9, 2.6, 2.6, 4.8),
            "ROE (%)": _row(-5.0, 1.7, 1.7, 3.0, 7.8),
            "ROCE (%)": _row(-8.3, -2.3, -0.7, 0.0, 6.2),
            "Receivables (days)": _row(23.6, 23.9, 35.1, 34.5, 33.2),
            "Inventory (days)": _row(21.7, 11.1, 11.5, 11.3, 11.0),
            "Payables (days)": _row(177.7, 112.2, 100.7, 102.2, 104.6),
            "Current ratio (x)": _row(7.5, 2.6, 3.5, 2.6, 2.2),
            "Quick ratio (x)": _row(4.1, 1.3, 2.4, 1.8, 1.6),
            "Gross asset T.O (x)": _row(28.2, 27.2, 20.4, 17.6, 17.5),
            "Total asset T.O (x)": _row(0.4, 0.5, 0.7, 0.9, 1.3),
            "Int. covge. ratio (x)": _row(-33.6, -6.7, -1.5, 0.1, 10.6),
            "Adj. debt/equity (x)": _row(0.0, 0.0, 0.1, 0.1, 0.1),
            "EV/Sales (x)": _row(6.1, 13.3, 9.5, 8.6, 5.5),
            "EV/EBITDA (x)": _row(None, 3825.7, 302.2, 240.3, 84.0),
            "P/E (x)": _row(None, 4448.0, 335.8, 325.2, 114.1),
            "P/BV (x)": _row(2.2, 7.9, 6.4, 9.6, 8.9),
        },
        recommendation_history=[
            RecommendationRow(date="11-Aug-22", rating="BUY", target=69),
            RecommendationRow(date="17-Feb-23", rating="BUY", target=60),
            RecommendationRow(date="08-Aug-23", rating="BUY", target=114),
            RecommendationRow(date="13-Feb-24", rating="BUY", target=174),
            RecommendationRow(date="16-May-24", rating="BUY", target=220),
            RecommendationRow(date="28-Oct-24", rating="BUY", target=284),
            RecommendationRow(date="30-Jan-25", rating="BUY", target=254),
            RecommendationRow(date="29-Jul-25", rating="HOLD", target=337),
        ],
        price_1y=_price_1y(),
        price_3y=_price_3y(),
    )
