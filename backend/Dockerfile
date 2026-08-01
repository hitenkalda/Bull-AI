# Backend: FastAPI + Playwright (Chromium) for HTML->PDF rendering.
#
# We base on the official Playwright Python image, which already ships Chromium
# and every native OS dependency it needs — this is why we render with
# Playwright rather than the spec's WeasyPrint (which would require libpango /
# libcairo / libgdk-pixbuf system packages). The image tag's browser build is
# matched by the pinned playwright==1.44.0 in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python deps first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium is preinstalled in this image; ensure the pip-pinned build is present.
RUN playwright install chromium

COPY . .

EXPOSE 8000

# GEMINI_API_KEY is optional — absent -> deterministic mock extraction.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
