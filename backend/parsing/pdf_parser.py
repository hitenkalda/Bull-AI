"""Extract text and tables from a PDF using pdfplumber."""
from __future__ import annotations

from typing import List

import pdfplumber


def parse_pdf_text(data: bytes) -> str:
    """Return concatenated text + flattened tables from every page.

    Tables are appended as tab-separated rows so the LLM sees tabular structure
    even when the raw text stream loses column alignment.
    """
    import io

    chunks: List[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages):
            chunks.append(f"\n===== PAGE {i + 1} =====")
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
            for t_index, table in enumerate(page.extract_tables() or []):
                chunks.append(f"\n--- table {i + 1}.{t_index + 1} ---")
                for row in table:
                    cells = ["" if c is None else str(c).replace("\n", " ") for c in row]
                    chunks.append("\t".join(cells))
    return "\n".join(chunks).strip()
