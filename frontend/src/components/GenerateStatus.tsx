import { Stage, StageState } from "../api/generateReport";

export interface StageProgress {
  key: string;
  label: string;
  state: StageState;
  detail?: string | null;
}

export type Status =
  | { kind: "idle" }
  | { kind: "loading"; stages: StageProgress[]; elapsed: number }
  | { kind: "error"; message: string }
  | { kind: "done"; url: string; filename: string };

interface Props {
  status: Status;
  onReset: () => void;
}

function fmtElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function initialStages(stages: Stage[]): StageProgress[] {
  return stages.map((s) => ({ key: s.key, label: s.label, state: "pending" }));
}

export default function GenerateStatus({ status, onReset }: Props) {
  if (status.kind === "idle") return null;

  if (status.kind === "loading") {
    const total = status.stages.length;
    const settled = status.stages.filter(
      (s) => s.state === "done" || s.state === "skipped",
    ).length;
    const pct = total ? Math.round((settled / total) * 100) : 0;

    return (
      <div className="status status--loading">
        <div className="progress-head">
          <strong>Generating your report…</strong>
          <span className="progress-elapsed">{fmtElapsed(status.elapsed)}</span>
        </div>

        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>

        <ol className="stage-list">
          {status.stages.map((s) => (
            <li key={s.key} className={`stage stage--${s.state}`}>
              <span className="stage-icon" aria-hidden="true">
                {s.state === "done" ? (
                  "✓"
                ) : s.state === "skipped" ? (
                  "–"
                ) : s.state === "active" ? (
                  <span className="spinner spinner--sm" />
                ) : (
                  "○"
                )}
              </span>
              <span className="stage-body">
                <span className="stage-label">{s.label}</span>
                {s.detail && <span className="stage-detail">{s.detail}</span>}
              </span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  if (status.kind === "error") {
    return (
      <div className="status status--error">
        <p>
          <strong>Something went wrong.</strong> {status.message}
        </p>
        <button className="btn btn--ghost" onClick={onReset}>
          Try again
        </button>
      </div>
    );
  }

  // done
  return (
    <div className="status status--done">
      <p>
        <strong>Report ready.</strong> Your PDF has been generated.
      </p>
      <div className="status-actions">
        <a className="btn" href={status.url} download={status.filename}>
          Download PDF
        </a>
        <a className="btn btn--ghost" href={status.url} target="_blank" rel="noreferrer">
          Preview
        </a>
        <button className="btn btn--ghost" onClick={onReset}>
          Generate another
        </button>
      </div>
    </div>
  );
}
