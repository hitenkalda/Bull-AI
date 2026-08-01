"""Gemini multimodal structured extraction with retry + graceful fallback."""
from __future__ import annotations

import json
from typing import List, Optional

from config import settings
from models.schema import CompanyReport

from .prompt import build_prompt


def _coerce_json(text: str) -> dict:
    """Pull a JSON object out of the model response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def extract_report(
    company_name: str,
    source_text: str,
    images: Optional[List[bytes]] = None,
) -> CompanyReport:
    """Call Gemini and validate into CompanyReport.

    On any failure after one retry, fall back to a null-filled report so the
    pipeline always yields a renderable document (missing fields -> "N/A").
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = build_prompt(company_name, source_text)

    parts: List[object] = [prompt]
    for img in (images or [])[: settings.max_pdf_pages_to_image]:
        parts.append(types.Part.from_bytes(data=img, mime_type="image/png"))

    config = types.GenerateContentConfig(response_mime_type="application/json")

    last_err: Optional[Exception] = None
    for attempt in range(2):  # initial + one retry
        try:
            resp = client.models.generate_content(
                model=settings.gemini_model, contents=parts, config=config
            )
            data = _coerce_json(resp.text)
            data.setdefault("company_name", company_name)
            return CompanyReport.model_validate(data)
        except Exception as e:  # noqa: BLE001 - broad by design; we degrade gracefully
            last_err = e
            print(
                f"[extraction] attempt {attempt + 1}/2 failed "
                f"(model={settings.gemini_model!r}): {type(e).__name__}: {e}"
            )
            continue

    # Fallback: minimal null-filled report keyed on the company name.
    print(
        "[extraction] all attempts failed -> returning null-filled report "
        f"(every field renders 'N/A'). Last error: {last_err!r}"
    )
    return CompanyReport(company_name=company_name)
