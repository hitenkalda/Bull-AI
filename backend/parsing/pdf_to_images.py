"""Rasterize the most report-relevant pages of a PDF to PNG bytes (PyMuPDF).

The images feed Gemini's multimodal prompt so the model can read layout/tables
that text extraction mangles (as seen in the Geojit reference).

Large decks (e.g. a 49-page results presentation) bury the financial statements
deep in the document, so a naive "first N pages" misses them. We instead always
keep the leading pages (headline / highlights) and then prioritise pages whose
text mentions financial-statement keywords, up to the page budget.
"""
from __future__ import annotations

from typing import List

import fitz  # PyMuPDF

# Pages whose text mentions these earn a spot in the image budget. Statement-
# specific phrases are weighted far above generic words like "revenue"/"ratio"
# that also litter operational slides, so the true financial pages win the budget.
_FINANCIAL_KEYWORDS = {
    "financial results": 10,
    "consolidated financial": 10,
    "profit & loss": 10,
    "profit and loss": 10,
    "statement of profit": 10,
    "balance sheet": 8,
    "cash flow": 8,
    "cashflow": 8,
    "profit after tax": 6,
    "profit before tax": 6,
    "finance cost": 5,
    "net worth": 4,
    "net debt": 4,
    "borrowings": 4,
    "reserves": 4,
    "depreciation": 3,
    "diluted eps": 3,
    "ebitda margin": 3,
    "ebitda": 1,
    "revenue": 1,
    "ratio": 1,
}

# Always image at least this many leading pages regardless of keywords: the
# cover / highlights / headline generally live up front.
_ALWAYS_LEADING = 3


def _select_pages(doc: "fitz.Document", max_pages: int) -> List[int]:
    """Choose which 0-based page indices to rasterize, in document order."""
    total = doc.page_count
    if total <= max_pages:
        return list(range(total))

    selected = set(range(min(_ALWAYS_LEADING, total)))

    # Score remaining pages by financial-keyword hits and take the richest ones.
    scored: List[tuple] = []
    for i in range(total):
        if i in selected:
            continue
        try:
            text = (doc[i].get_text() or "").lower()
        except Exception:  # noqa: BLE001 - a bad page shouldn't abort selection
            text = ""
        score = sum(weight * text.count(kw) for kw, weight in _FINANCIAL_KEYWORDS.items())
        if score:
            scored.append((score, i))

    scored.sort(key=lambda t: (-t[0], t[1]))
    for _, idx in scored:
        if len(selected) >= max_pages:
            break
        selected.add(idx)

    # If keyword pages didn't fill the budget, top up with more leading pages.
    for i in range(total):
        if len(selected) >= max_pages:
            break
        selected.add(i)

    return sorted(selected)


def pdf_to_images(data: bytes, max_pages: int = 6, dpi: int = 150) -> List[bytes]:
    images: List[bytes] = []
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        for idx in _select_pages(doc, max_pages):
            pix = doc[idx].get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images
