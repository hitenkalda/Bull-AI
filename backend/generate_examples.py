"""Generate the example PDFs shipped in ../examples/.

Run from the backend/ directory:

    python generate_examples.py

Produces two structurally-identical reports from deterministic mock data (no
Gemini key required):

  * Eternal_Ltd_Q1FY26.pdf  — a fully-populated report (mirrors the Geojit sample)
  * POCL_Q2FY26.pdf         — a deliberately sparse deck, demonstrating that
                              missing sections/fields degrade to "N/A" / omitted
                              sections instead of crashing or breaking the layout.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extraction.mock import mock_report                # noqa: E402
from extraction.mock_partial import partial_report      # noqa: E402
from extraction.normalize import normalize_report        # noqa: E402
from rendering.pdf_renderer import save_report_pdf       # noqa: E402

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def main() -> None:
    jobs = [
        (mock_report("Eternal Ltd."), "Eternal_Ltd_Q1FY26.pdf"),
        (partial_report("Pondy Oxides & Chemicals Ltd."), "POCL_Q2FY26.pdf"),
    ]
    for report, name in jobs:
        out_path = os.path.join(_OUT, name)
        # Run the same deterministic normalization the live pipeline applies.
        save_report_pdf(normalize_report(report), out_path)
        print(f"wrote {out_path}  ({os.path.getsize(out_path):,} bytes)")


if __name__ == "__main__":
    main()
