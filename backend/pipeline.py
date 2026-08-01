"""End-to-end orchestration: upload bytes -> parsed input -> extraction -> PDF."""
from __future__ import annotations

from typing import Optional

from config import settings
from enrichment.market_data import enrich_with_market_data
from extraction.gemini_client import extract_report
from extraction.mock import mock_report
from extraction.normalize import normalize_report
from models.schema import CompanyReport
from parsing.dispatch import parse_upload
from progress import Reporter
from rendering.pdf_renderer import render_report_pdf


def build_report(
    company_name: str,
    filename: str,
    data: bytes,
    reporter: Optional[Reporter] = None,
) -> CompanyReport:
    """Parse the upload and extract a structured report (mock if no API key)."""
    if reporter is None:
        reporter = Reporter()

    reporter.start("parse")
    parsed = parse_upload(filename, data, max_pdf_pages=settings.max_pdf_pages_to_image)
    reporter.done("parse", f"Parsed {len(parsed.text):,} chars, {len(parsed.images)} page images")

    if settings.use_mock:
        # No API key -> deterministic sample so the pipeline still works.
        reporter.skip("extract", "No API key — using sample data")
        reporter.skip("market")
        reporter.start("normalize")
        report = normalize_report(mock_report(company_name))
        reporter.done("normalize")
        return report

    reporter.start("extract")
    report = extract_report(company_name, parsed.text, parsed.images)
    reporter.done("extract")

    if settings.enable_market_data:
        # Fill only the market fields the deck left N/A (never overwrite extracted
        # values). Best-effort: offline / lookup failure leaves the report as-is.
        reporter.start("market")
        try:
            report = enrich_with_market_data(report, reporter=reporter)
            reporter.done("market")
        except Exception as exc:  # pragma: no cover - defensive
            reporter.done("market", f"Skipped: {exc}")
            print(f"[market-data] enrichment skipped: {exc}")
    else:
        reporter.skip("market")

    reporter.start("normalize")
    report = normalize_report(report)
    reporter.done("normalize")

    return report


def generate_pdf(
    company_name: str,
    filename: str,
    data: bytes,
    reporter: Optional[Reporter] = None,
) -> bytes:
    report = build_report(company_name, filename, data, reporter=reporter)
    if reporter is not None:
        reporter.start("render")
    pdf = render_report_pdf(report)
    if reporter is not None:
        reporter.done("render")
    return pdf
