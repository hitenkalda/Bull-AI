// Thin client for the FastAPI backend. Returns a Blob (the generated PDF)
// on success, or throws an Error carrying the backend's detail message.

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export interface GenerateArgs {
  companyName: string;
  file: File;
}

export async function generateReport({
  companyName,
  file,
}: GenerateArgs): Promise<Blob> {
  const form = new FormData();
  form.append("company_name", companyName);
  form.append("file", file);

  const res = await fetch(`${API_BASE}/api/generate-report`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep the status message */
    }
    throw new Error(detail);
  }

  return res.blob();
}

export interface Stage {
  key: string;
  label: string;
}

export type StageState = "pending" | "active" | "done" | "skipped";

export interface ProgressEvent {
  type: "stages" | "progress" | "tick" | "done" | "error";
  stages?: Stage[];
  state?: "start" | "done" | "skip" | "note";
  stage?: string;
  label?: string;
  detail?: string | null;
  filename?: string;
  pdf?: string;
}

function base64ToBlob(b64: string, mime: string): Blob {
  const bytes = atob(b64);
  const buf = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i);
  return new Blob([buf], { type: mime });
}

/**
 * Streaming variant: invokes onEvent for each stage update, resolves with the
 * finished PDF. Falls back to the plain endpoint if streaming isn't available.
 */
export async function generateReportStreaming(
  { companyName, file }: GenerateArgs,
  onEvent: (e: ProgressEvent) => void,
): Promise<{ blob: Blob; filename: string }> {
  const form = new FormData();
  form.append("company_name", companyName);
  form.append("file", file);

  const res = await fetch(`${API_BASE}/api/generate-report/stream`, {
    method: "POST",
    body: form,
  });

  if (!res.ok || !res.body) {
    // Backend too old / streaming blocked — fall back to the blocking endpoint.
    const blob = await generateReport({ companyName, file });
    return {
      blob,
      filename: `${companyName.replace(/[^A-Za-z0-9._-]+/g, "_")}_report.pdf`,
    };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: { blob: Blob; filename: string } | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      let event: ProgressEvent;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue;
      }
      if (event.type === "error") throw new Error(event.detail ?? "Generation failed");
      if (event.type === "done" && event.pdf) {
        result = {
          blob: base64ToBlob(event.pdf, "application/pdf"),
          filename:
            event.filename ??
            `${companyName.replace(/[^A-Za-z0-9._-]+/g, "_")}_report.pdf`,
        };
      } else {
        onEvent(event);
      }
    }
  }

  if (!result) throw new Error("Stream ended before the report was delivered.");
  return result;
}

export interface HealthInfo {
  status: string;
  mode: "mock" | "gemini";
  model: string;
  stages?: Stage[];
}

export async function getHealth(): Promise<HealthInfo> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}
