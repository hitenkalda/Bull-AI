# Bull AI — Financial Research Report Generator

Turn a company's financial document into a polished, four-page equity-research
PDF laid out to closely mirror a **Geojit** research note — same masthead, rating
box, company-data block, quarterly and annual tables, combo charts and
price-history lines.

Enter a company name, upload a PDF / CSV / TXT, and watch a live progress
checklist while Google **Gemini** extracts the numbers, `yfinance` fills in live
market data, and headless Chromium prints the report.

Missing data degrades gracefully: individual values render `N/A`, and whole
sections either hide themselves or show an explicit *"Not disclosed in source
document."* note. The layout never breaks.

---

## Contents

- [Quick start](#quick-start)
- [Running locally without Docker](#running-locally-without-docker)
- [Example outputs](#example-outputs)
- [How it works](#how-it-works)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [Where the template fields live](#where-the-template-fields-live)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Verifying a change](#verifying-a-change)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)

---

## Quick start

```bash
docker compose up -d --build
```

- Frontend UI → http://localhost:5173
- Backend API → http://localhost:8000 (health: `/api/health`)

The backend image installs Chromium for Playwright, so the **first** build takes
a few minutes and the container needs roughly 30–60 s to report healthy. Watch it
with:

```bash
docker compose logs -f backend
```

> Use `-d`. Running `docker compose up --build` attached inside a shell that is
> still waiting on a continuation prompt can create the containers without ever
> starting them — see [Troubleshooting](#troubleshooting).

**No API key required.** With `GEMINI_API_KEY` unset the backend runs in
deterministic **mock mode** (golden sample data), so the entire pipeline works
end-to-end offline. For live extraction:

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY=your_key_here
docker compose up -d --build
```

Get a key from [Google AI Studio](https://aistudio.google.com/apikey). The badge
in the UI header tells you which mode you are in.

---

## Running locally without Docker

**Backend** (Python 3.9+):

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn main:app --reload --port 8000
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Vite serves on http://localhost:5173 and proxies `/api` to port 8000.

---

## Example outputs

Two generated PDFs live in [`examples/`](./examples):

| File | Demonstrates |
|------|--------------|
| [`Eternal_Ltd_Q1FY26.pdf`](./examples/Eternal_Ltd_Q1FY26.pdf) | Full, data-rich broker note — every section, table and chart populated. A faithful Geojit clone. |
| [`POCL_Q2FY26.pdf`](./examples/POCL_Q2FY26.pdf) | **Graceful degradation** plus the deck-oriented sections: operational KPIs, capacity profile, entity-wise financials, investment rationale and key concerns, with `N/A` cells and *"Not disclosed"* blocks where the source is silent. |

Regenerate them at any time (mock data, no key needed):

```bash
cd backend
python generate_examples.py
```

---

## How it works

```
upload ─► parse ─► extract (Gemini | mock) ─► market data ─► normalize ─► render
           │           │                          │             │           │
        pdfplumber  google-genai              yfinance     derived      Jinja2 +
        + PyMuPDF   JSON mode                              charts      Playwright
```

Every step reports itself to the browser as it runs, so a 20–60 s job is never a
silent spinner. The five stages are defined once in
[`backend/progress.py`](./backend/progress.py) and consumed by both the SSE
endpoint and the React checklist:

| Stage | Key | What happens |
|-------|-----|--------------|
| Reading document | `parse` | PDF text + tables via `pdfplumber`; the first 6 pages are also rasterized at 150 DPI with PyMuPDF for the multimodal prompt. CSV via `pandas`, TXT decoded directly. |
| Extracting financials with AI | `extract` | Gemini is asked for strict JSON (`response_mime_type: application/json`) against the `CompanyReport` schema. One retry, then a null-filled fallback. Skipped in mock mode. |
| Fetching live market data | `market` | `yfinance` fills **only** the market fields extraction left empty — CMP, market cap, 52-week range, beta, dividend yield, price history. Best-effort: any failure is logged and skipped, never fatal. |
| Deriving charts & metrics | `normalize` | Growth rates, margins and the revenue / EBITDA / PAT chart series are computed deterministically from the extracted P&L, falling back to the quarterly table. Model-supplied series are never overwritten. |
| Rendering PDF | `render` | Charts become base64 PNGs, Jinja fills the template, Playwright prints A4 with `print_background`. |

Charts and headings follow the data: the entity chart falls back Revenue → EBITDA
and disappears entirely if both are absent, and each chart's heading uses the
label derived from the source, so a "Net Interest Income" series is never
mislabelled "Revenue".

---

## API reference

### `POST /api/generate-report`

Blocking. Multipart form:

| Field | Type | Notes |
|-------|------|-------|
| `company_name` | text | Used in the masthead and the download filename. |
| `file` | file | PDF, CSV or TXT. Max 15 MB by default. |

Returns `application/pdf` as an attachment.

```bash
curl -X POST http://localhost:8000/api/generate-report \
  -F "company_name=ICICI Bank" \
  -F "file=@ICICI_Q2FY26.pdf" \
  -o ICICI_report.pdf
```

Errors: `400` empty upload, `413` over the size limit, `415` unsupported type,
`500` generation failure (message in `detail`).

### `POST /api/generate-report/stream`

Same work and same form fields, but streams **Server-Sent Events** so the client
can show live progress. The finished PDF arrives base64-encoded in the
terminating event, which keeps the server completely stateless — no job IDs, no
polling, no temp files.

```bash
curl -N -X POST http://localhost:8000/api/generate-report/stream \
  -F "company_name=ICICI Bank" \
  -F "file=@ICICI_Q2FY26.pdf"
```

Event types, all delivered as `data: {json}`:

| `type` | Payload | Meaning |
|--------|---------|---------|
| `stages` | `stages: [{key, label}]` | Sent first so the UI can render every row greyed out. |
| `progress` | `state`, `stage`, `label`, `detail` | `state` is `start`, `done`, `skip` or `note`. `note` is a sub-status on the row already running (e.g. which ticker resolved). |
| `tick` | — | Heartbeat, once a second while work is in flight. Keeps proxies from idling out during the long opaque Gemini call. |
| `done` | `filename`, `pdf` (base64) | Terminal success. |
| `error` | `detail` | Terminal failure. |

The frontend client in
[`frontend/src/api/generateReport.ts`](./frontend/src/api/generateReport.ts)
consumes this with `fetch` + a `ReadableStream` reader rather than `EventSource`,
because `EventSource` cannot issue a multipart POST. If the stream is
unavailable it transparently falls back to the blocking endpoint.

### `GET /api/health`

```json
{
  "status": "ok",
  "mode": "gemini",
  "model": "gemini-flash-latest",
  "stages": [{ "key": "parse", "label": "Reading document" }]
}
```

`mode` is `mock` when no API key is configured. The UI reads `stages` on load so
the checklist matches the backend without hardcoding labels.

---

## Configuration

Set in `.env` (compose) or `backend/.env` (local). See the matching
`.env.example` files; both are committed as templates.

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | *(empty)* | Blank ⇒ deterministic mock mode. Set it for live extraction. |
| `GEMINI_MODEL` | `gemini-flash-latest` | Model used for multimodal structured extraction. |
| `MAX_UPLOAD_MB` | `15` | Uploads above this are rejected with `413`. |
| `MAX_PDF_PAGES_TO_IMAGE` | `6` | How many PDF pages get rasterized for the multimodal prompt. More pages means better extraction but a slower, pricier call. |
| `ENABLE_MARKET_DATA` | `true` | Set `false` to skip the `yfinance` enrichment stage entirely. |

---

## Where the template fields live

The layout and its field mapping are deliberately isolated, so the template can
be retargeted without touching the pipeline:

- **[`backend/rendering/templates/report.html.jinja`](./backend/rendering/templates/report.html.jinja)** — the four-page layout (HTML + print CSS). All section structure and table columns. Every optional block is wrapped in `{% if %}` so absent data hides the section rather than leaving a stranded heading.
- **[`backend/rendering/template_fields.py`](./backend/rendering/template_fields.py)** — value → string mapping and the central `None → "N/A"` convention (`fmt_num`, `fmt_pct`, `fmt_growth`, `fmt_price`, `fmt_str`), plus `build_template_context()`.
- **[`backend/models/schema.py`](./backend/models/schema.py)** — the Pydantic `CompanyReport`: the contract between extraction and rendering. Add a field here, surface it in the template, describe it in the prompt.
- **[`backend/rendering/charts.py`](./backend/rendering/charts.py)** — chart builders (teal/orange combo bars + line, teal/grey price lines) → base64 data-URIs. Font sizes are centralized in the `FS_*` constants near the top.
- **[`backend/progress.py`](./backend/progress.py)** — the stage list shared by the API and the UI. Add a stage here and both sides pick it up.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Uvicorn (Python 3.9-compatible) |
| LLM extraction | Google Gemini (`google-genai`), multimodal, JSON mode |
| Market data | `yfinance` (fills only empty fields) |
| Parsing | `pdfplumber`, `PyMuPDF`, `pandas` |
| Charts | `matplotlib` (Agg) → base64 PNG |
| Templating | Jinja2 (HTML + print CSS) |
| HTML → PDF | Playwright (headless Chromium) |
| Progress | Server-Sent Events over a worker-thread → asyncio queue bridge |
| Schema | Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite 5 |
| Packaging | Docker + docker-compose, nginx serving the SPA |

### Playwright instead of WeasyPrint

The original spec suggested WeasyPrint for HTML → PDF. This build uses
**Playwright (headless Chromium)** for two reasons: WeasyPrint needs native GTK
libraries (libpango / libcairo / libgdk-pixbuf) unavailable on the target Windows
dev machine, and Chromium renders CSS with higher fidelity, which matters for
matching the Geojit layout closely. The renderer keeps a swappable contract
(`render_html` / `html_to_pdf` in `rendering/pdf_renderer.py`), so moving back is
a localized change.

---

## Project structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app: blocking + SSE endpoints, health
│   ├── pipeline.py              # upload -> report -> PDF orchestration
│   ├── progress.py              # stage contract + Reporter (shared with the UI)
│   ├── config.py                # env settings, mock-mode toggle
│   ├── generate_examples.py     # writes examples/*.pdf
│   ├── _check_fit.py            # verifies every page fits on A4
│   ├── models/schema.py         # Pydantic CompanyReport
│   ├── parsing/                 # pdf / csv / txt -> text + page images
│   ├── extraction/              # gemini_client, prompt, normalize, mock, mock_partial
│   ├── enrichment/market_data.py# yfinance backfill
│   └── rendering/               # charts, template_fields, pdf_renderer, templates/
├── frontend/
│   ├── src/App.tsx              # SSE event -> checklist state
│   ├── src/api/generateReport.ts# streaming + blocking clients
│   ├── src/components/          # UploadForm, GenerateStatus (progress checklist)
│   └── nginx.conf               # SPA + /api proxy, buffering off for SSE
├── examples/                    # two generated sample PDFs
├── docker-compose.yml
└── .env.example
```

---

## Verifying a change

The template must stay exactly four A4 pages. After touching CSS, fonts or chart
sizes, run the page-fit check — it renders both mock reports in Chromium and
measures each page against the A4 limit of ~1123 px:

```bash
cd backend
python _check_fit.py
```

Then regenerate the examples and confirm both are still four pages:

```bash
cd backend
python generate_examples.py
```

Frontend type check:

```bash
cd frontend
npx tsc --noEmit
```

---

## Troubleshooting

**Containers say `Created` but never `Started`.** Running `docker compose up
--build` attached from a shell still sitting at a `>>` continuation prompt can
create containers without starting them. Check with `docker compose ps -a`, then:

```bash
docker compose up -d --build
```

**`/api/health` returns nothing right after starting.** The backend installs and
launches Chromium; give it 30–60 s. `docker compose logs -f backend` shows when
Uvicorn is listening, and the container reports `(healthy)` once the healthcheck
passes.

**Progress arrives all at once instead of live.** Something is buffering the
stream. The backend sends `X-Accel-Buffering: no` and `nginx.conf` sets
`proxy_buffering off`, but another proxy in front of the app may re-buffer it.

**Company Data shows `N/A`.** Market enrichment needs a ticker code in the
extracted report. Look for `[market-data]` lines in the backend logs — every
failure path explains itself (no ticker found, lookup failed, nothing resolved).

**`ImportError` / DLL failure from `fitz` on Windows.** PyMuPDF wheels can fail
to load on some Windows + Python 3.9 combinations. The Docker image is
unaffected; run there, or use CSV / TXT input, which does not touch PyMuPDF.

**Charts missing from the PDF.** A chart renders only when its series has data.
Empty series hide the whole cell by design rather than printing an axis over
blank space.

---

## Security notes

- Secrets live only in `.env` / `backend/.env`, both git-ignored at every
  directory depth. Only the `.env.example` templates are committed. Rotate your
  key immediately if it ever lands in a commit.
- The API key is read server-side only and is never sent to the browser;
  `/api/health` exposes the model name and mode, never the key.
- Uploads are validated for emptiness and size before any work starts, and
  unsupported types are rejected outright.
- Download filenames are sanitized against a strict allowlist
  (`[^A-Za-z0-9._-]`) to avoid header injection and path traversal.
- Nothing is persisted. Uploads are processed in memory and the PDF is returned
  in the response; no document or extraction is written to disk or logged.
- CORS currently allows all origins, which suits local development. Restrict
  `allow_origins` in `backend/main.py` before any real deployment.
- The API is unauthenticated by design for this demo. Add authentication and
  rate limiting before exposing it beyond localhost — Gemini calls cost money,
  so an open endpoint is a billing risk as much as a security one.

---

## Disclaimer

Generated reports are produced automatically for demonstration purposes only and
are **not investment advice**.
