"""FastAPI app: generate endpoints (plain + progress-streaming) + health check."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import re
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from config import settings
from parsing.dispatch import UnsupportedFileType
from pipeline import generate_pdf
from progress import STAGES, Reporter

app = FastAPI(title="Bull AI — Financial Research Report Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "report"
    return slug


def _validate_upload(data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_mb} MB limit.",
        )


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "mock" if settings.use_mock else "gemini",
            "model": settings.gemini_model,
            "stages": [{"key": k, "label": v} for k, v in STAGES]}


@app.post("/api/generate-report")
async def generate_report(
    company_name: str = Form(...),
    file: UploadFile = File(...),
):
    data = await file.read()
    _validate_upload(data)

    try:
        # generate_pdf drives Playwright's sync API, which cannot run on the
        # asyncio event loop — offload it to a worker thread.
        pdf_bytes = await run_in_threadpool(
            generate_pdf, company_name.strip() or "Company", file.filename or "upload", data
        )
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    fname = f"{_safe_filename(company_name)}_report.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _sse(event: dict) -> str:
    """Serialize one Server-Sent Event frame."""
    return f"data: {json.dumps(event)}\n\n"


@app.post("/api/generate-report/stream")
async def generate_report_stream(
    company_name: str = Form(...),
    file: UploadFile = File(...),
):
    """Same work as /api/generate-report, but streams stage progress first.

    A run is 20-60s and mostly one opaque Gemini call, so the client gets a live
    checklist over SSE and the finished PDF (base64) in the terminating event.
    Keeping the PDF in-band avoids server-side job state entirely.
    """
    data = await file.read()
    _validate_upload(data)
    name = company_name.strip() or "Company"
    filename = file.filename or "upload"

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def sink(event: dict) -> None:
        # Called from the worker thread — hop back onto the event loop.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    async def run() -> None:
        try:
            pdf = await run_in_threadpool(
                generate_pdf, name, filename, data, Reporter(sink)
            )
            await queue.put({
                "type": "done",
                "filename": f"{_safe_filename(company_name)}_report.pdf",
                "pdf": base64.b64encode(pdf).decode("ascii"),
            })
        except UnsupportedFileType as e:
            await queue.put({"type": "error", "detail": str(e)})
        except Exception as e:  # noqa: BLE001
            await queue.put({"type": "error", "detail": f"Report generation failed: {e}"})
        finally:
            await queue.put({"type": "__eof__"})

    async def stream() -> AsyncIterator[str]:
        task = loop.create_task(run())
        # Announce the checklist up front so the UI can render every row greyed.
        yield _sse({"type": "stages", "stages": [{"key": k, "label": v} for k, v in STAGES]})
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Heartbeat: keeps proxies from idling out and lets the UI
                    # tick an elapsed timer during the long extraction stage.
                    yield _sse({"type": "tick"})
                    continue
                if event.get("type") == "__eof__":
                    break
                yield _sse(event)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # tell nginx not to buffer the stream
        },
    )
