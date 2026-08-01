import { useEffect, useRef, useState } from "react";
import UploadForm from "./components/UploadForm";
import GenerateStatus, { initialStages, Status, StageProgress } from "./components/GenerateStatus";
import { generateReportStreaming, getHealth, HealthInfo } from "./api/generateReport";

export default function App() {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  // Clear the elapsed-time interval on unmount.
  useEffect(() => stopTimer, []);

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function handleSubmit(companyName: string, file: File) {
    const startedAt = Date.now();
    setStatus({
      kind: "loading",
      stages: initialStages(health?.stages ?? []),
      elapsed: 0,
    });

    // Tick the elapsed counter locally — independent of server heartbeats.
    stopTimer();
    timerRef.current = window.setInterval(() => {
      setStatus((s) =>
        s.kind === "loading"
          ? { ...s, elapsed: Math.floor((Date.now() - startedAt) / 1000) }
          : s,
      );
    }, 1000);

    try {
      const { blob, filename } = await generateReportStreaming(
        { companyName, file },
        (event) => {
          if (event.type === "stages" && event.stages) {
            const fresh = initialStages(event.stages);
            setStatus((s) => (s.kind === "loading" ? { ...s, stages: fresh } : s));
            return;
          }
          if (event.type !== "progress" || !event.stage) return;

          setStatus((s) => {
            if (s.kind !== "loading") return s;
            const stages: StageProgress[] = s.stages.map((row) => {
              if (row.key !== event.stage) return row;
              if (event.state === "start")
                return { ...row, state: "active", detail: event.detail ?? null };
              if (event.state === "done")
                return { ...row, state: "done", detail: event.detail ?? row.detail };
              if (event.state === "skip")
                return { ...row, state: "skipped", detail: event.detail ?? null };
              // "note" — sub-status on the row that's already running.
              return { ...row, detail: event.detail ?? row.detail };
            });
            return { ...s, stages };
          });
        },
      );

      stopTimer();
      setStatus({ kind: "done", url: URL.createObjectURL(blob), filename });
    } catch (err) {
      stopTimer();
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "Unknown error",
      });
    }
  }

  function reset() {
    setStatus((s) => {
      if (s.kind === "done") URL.revokeObjectURL(s.url);
      return { kind: "idle" };
    });
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark">Bull&nbsp;AI</span>
          <span className="brand-sub">Financial Research Report Generator</span>
        </div>
        {health && (
          <span className={`badge badge--${health.mode}`}>
            {health.mode === "gemini"
              ? `Live · ${health.model}`
              : "Mock data mode"}
          </span>
        )}
      </header>

      <main className="main">
        <p className="lede">
          Enter a company name and upload its financial context document. Bull AI
          extracts the numbers and renders a Geojit-style equity research report.
        </p>

        <UploadForm disabled={status.kind === "loading"} onSubmit={handleSubmit} />
        <GenerateStatus status={status} onReset={reset} />
      </main>

      <footer className="foot">
        Generated reports are for demonstration only and are not investment advice.
      </footer>
    </div>
  );
}
