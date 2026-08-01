import { useRef, useState } from "react";

const ACCEPTED = ".pdf,.csv,.txt";

interface Props {
  disabled: boolean;
  onSubmit: (companyName: string, file: File) => void;
}

export default function UploadForm({ disabled, onSubmit }: Props) {
  const [companyName, setCompanyName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const canSubmit = companyName.trim().length > 0 && file !== null && !disabled;

  function pickFile(f: File | null) {
    if (!f) return;
    const ok = /\.(pdf|csv|txt)$/i.test(f.name);
    if (!ok) {
      alert("Please upload a PDF, CSV, or TXT file.");
      return;
    }
    setFile(f);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (canSubmit && file) onSubmit(companyName.trim(), file);
  }

  return (
    <form className="card" onSubmit={submit}>
      <label className="field">
        <span className="field-label">Company name</span>
        <input
          type="text"
          placeholder="e.g. Eternal Ltd."
          value={companyName}
          disabled={disabled}
          onChange={(e) => setCompanyName(e.target.value)}
        />
      </label>

      <div className="field">
        <span className="field-label">Financial context document</span>
        <div
          className={`dropzone${dragging ? " dropzone--active" : ""}${
            file ? " dropzone--filled" : ""
          }`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pickFile(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          {file ? (
            <div className="dropzone-file">
              <strong>{file.name}</strong>
              <span>{(file.size / 1024).toFixed(0)} KB — click to replace</span>
            </div>
          ) : (
            <div className="dropzone-hint">
              <strong>Drop a file here</strong>
              <span>or click to browse — PDF, CSV or TXT</span>
            </div>
          )}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            hidden
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>

      <button type="submit" className="btn" disabled={!canSubmit}>
        {disabled ? "Generating…" : "Generate report"}
      </button>
    </form>
  );
}
