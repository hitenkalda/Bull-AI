"""Render the report: Jinja HTML -> PDF bytes via Playwright (Chromium).

Chromium's rendering engine reproduces the dense Geojit layout with high
fidelity. The module exposes the same interface the spec assigns to WeasyPrint
(render_html, html_to_pdf) so the engine can be swapped without touching callers.
"""
from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.schema import CompanyReport

from .charts import (
    render_capacity_chart,
    render_combo_chart,
    render_entity_chart_titled,
    render_price_chart,
)
from .template_fields import build_template_context

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_html(report: CompanyReport) -> str:
    entity_result = render_entity_chart_titled(
        report.entity_financials,
        report.entity_period_current,
        report.entity_period_prior,
    )
    charts = {
        "revenue": render_combo_chart(report.revenue_chart),
        "gov": render_combo_chart(report.gov_chart),
        "ebitda": render_combo_chart(report.ebitda_chart),
        "pat": render_combo_chart(report.pat_chart),
        "price_1y": render_price_chart(report.price_1y, figsize=(4.2, 1.85)),
        "price_3y": render_price_chart(report.price_3y, figsize=(5.4, 1.9), show_legend=False),
        "capacity": render_capacity_chart(report.capacity_profile),
        "entity": entity_result[0] if entity_result else None,
        "entity_measure": entity_result[1] if entity_result else None,
    }
    ctx = build_template_context(report, charts)
    template = _env.get_template("report.html.jinja")
    return template.render(**ctx)


def html_to_pdf(html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            prefer_css_page_size=True,
        )
        browser.close()
    return pdf


def render_report_pdf(report: CompanyReport) -> bytes:
    """Full render: report -> HTML -> PDF bytes."""
    return html_to_pdf(render_html(report))


def save_report_pdf(report: CompanyReport, out_path: str) -> str:
    pdf = render_report_pdf(report)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pdf)
    return out_path
