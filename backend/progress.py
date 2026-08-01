"""Progress reporting for the long-running generate pipeline.

A full run takes 20-60s, almost all of it inside one opaque Gemini call, so the
UI needs to say *which* stage is running rather than spinning silently. The
pipeline emits stage events through a ``Reporter``; the SSE endpoint forwards
them to the browser. ``Reporter()`` with no sink is a no-op, so the plain
(non-streaming) endpoint keeps working untouched.

Stage keys are the contract with the frontend checklist — keep STAGES in sync
with the labels rendered there.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

# (key, human label) in execution order. The frontend renders this as a
# checklist, so order matters and keys must stay stable.
STAGES: List[Tuple[str, str]] = [
    ("parse", "Reading document"),
    ("extract", "Extracting financials with AI"),
    ("market", "Fetching live market data"),
    ("normalize", "Deriving charts & metrics"),
    ("render", "Rendering PDF"),
]

_LABELS: Dict[str, str] = dict(STAGES)

Sink = Callable[[dict], None]


class Reporter:
    """Emits stage lifecycle events to a sink. No sink -> silent no-op."""

    def __init__(self, sink: Optional[Sink] = None) -> None:
        self._sink = sink

    def _emit(self, event: dict) -> None:
        if self._sink is None:
            return
        try:
            self._sink(event)
        except Exception:  # pragma: no cover - progress must never break a run
            pass

    def _stage(self, state: str, stage: str, detail: Optional[str]) -> None:
        self._emit({
            "type": "progress",
            "state": state,
            "stage": stage,
            "label": _LABELS.get(stage, stage),
            "detail": detail,
        })

    def start(self, stage: str, detail: Optional[str] = None) -> None:
        self._stage("start", stage, detail)

    def done(self, stage: str, detail: Optional[str] = None) -> None:
        self._stage("done", stage, detail)

    def skip(self, stage: str, detail: Optional[str] = None) -> None:
        """Stage won't run at all (e.g. market lookup in mock mode)."""
        self._stage("skip", stage, detail)

    def note(self, stage: str, detail: str) -> None:
        """Sub-status on the stage already running (keeps the same checklist row)."""
        self._stage("note", stage, detail)
