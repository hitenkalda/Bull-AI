"""Page-fit check: does every .page still fit inside one A4 sheet?

Renders the mock reports in Chromium and measures each .page element's
scrollHeight against the A4 content limit. A page that overflows silently
becomes two pages in the PDF, which breaks the fixed 4-page format, so this
runs after any font-size or layout change.

    python _check_fit.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extraction.mock import mock_report  # noqa: E402
from extraction.mock_partial import partial_report  # noqa: E402
from extraction.normalize import normalize_report  # noqa: E402
from rendering.pdf_renderer import render_html  # noqa: E402

A4_PX = 297 * 96 / 25.4  # A4 height in CSS px at 96dpi ~= 1123
TOLERANCE_PX = 1.0  # sub-pixel rounding on the min-height floor is not overflow


def measure(html: str):
    """Per-page (rendered_height, natural_content_height).

    ``.page`` has ``min-height:297mm; overflow:hidden``, so a page that fits
    always reports exactly the A4 height and an overflowing page reports more.
    Measuring the children's extent as well gives the true content height, so
    we can see remaining slack instead of just a pass/fail.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        rows = page.evaluate(
            """() => Array.from(document.querySelectorAll('.page')).map(el => {
                const top = el.getBoundingClientRect().top;
                let bottom = 0;
                for (const c of el.children) {
                    if (getComputedStyle(c).position === 'absolute') continue;
                    const r = c.getBoundingClientRect();
                    if (r.bottom > bottom) bottom = r.bottom;
                }
                const pad = parseFloat(getComputedStyle(el).paddingBottom) || 0;
                return [el.scrollHeight, bottom - top + pad];
            })"""
        )
        browser.close()
    return rows


def main() -> None:
    jobs = [
        ("Eternal", mock_report("Eternal Ltd.")),
        ("POCL", partial_report("Pondy Oxides & Chemicals Ltd.")),
    ]
    limit = A4_PX
    bad = False
    for name, report in jobs:
        rows = measure(render_html(normalize_report(report)))
        print(f"{name}: {len(rows)} page(s), limit {limit:.0f}px")
        for i, (rendered, content) in enumerate(rows, 1):
            over = rendered > limit + TOLERANCE_PX
            slack = limit - content
            flag = "OVERFLOW" if over else "ok"
            print(f"   page {i}: content {content:>7.1f}px  slack {slack:>7.1f}px  {flag}")
            if over:
                bad = True
        if len(rows) != 4:
            print(f"   !! expected 4 pages, got {len(rows)}")
            bad = True
    print("RESULT:", "OVERFLOW - fix before shipping" if bad else "all pages fit")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
