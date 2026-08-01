"""Parse CSV uploads into a compact text representation for the LLM."""
from __future__ import annotations

import io

import pandas as pd


def parse_csv_text(data: bytes) -> str:
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception:
        # Fall back to raw decode if pandas can't infer the dialect.
        return data.decode("utf-8", errors="replace")

    lines = [f"CSV with {len(df)} rows x {len(df.columns)} columns.",
             "Columns: " + ", ".join(map(str, df.columns))]
    # Cap rows sent to the model to keep the prompt bounded.
    lines.append(df.head(200).to_csv(index=False))
    return "\n".join(lines)
