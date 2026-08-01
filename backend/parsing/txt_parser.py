"""Plain-text upload parsing."""
from __future__ import annotations


def parse_txt_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()
