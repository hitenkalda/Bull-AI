"""Dispatch an uploaded file to the correct parser by extension/content type."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .csv_parser import parse_csv_text
from .pdf_parser import parse_pdf_text
from .pdf_to_images import pdf_to_images
from .txt_parser import parse_txt_text


@dataclass
class ParsedInput:
    text: str
    images: List[bytes] = field(default_factory=list)
    kind: str = "unknown"


class UnsupportedFileType(Exception):
    pass


def parse_upload(filename: str, data: bytes, max_pdf_pages: int = 6) -> ParsedInput:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return ParsedInput(
            text=parse_pdf_text(data),
            images=pdf_to_images(data, max_pages=max_pdf_pages),
            kind="pdf",
        )
    if name.endswith(".csv"):
        return ParsedInput(text=parse_csv_text(data), kind="csv")
    if name.endswith(".txt"):
        return ParsedInput(text=parse_txt_text(data), kind="txt")
    raise UnsupportedFileType(f"Unsupported file type: {filename!r}. Use PDF, CSV, or TXT.")
