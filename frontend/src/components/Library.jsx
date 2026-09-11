import { useRef, useState } from "react";

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Library({
  open,
  docs,
  uploading,
  error,
  onUpload,
  onDelete,
}) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [pendingId, setPendingId] = useState(null);

  function takeFiles(files) {
    const file = files?.[0];
    if (file) onUpload(file);
  }

  return (
    <aside className={`library${open ? " open" : ""}`} aria-label="Document library">
      <div className="panel-label">
        <span>Library</span>
        <span>{docs.length} docs</span>
      </div>

      <label
        className={`dropzone${drag ? " active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDrag(false);
          takeFiles(event.dataTransfer.files);
        }}
      >
        <p>{uploading ? "Indexing…" : "Drop a PDF, Markdown, or text file"}</p>
        <span>Files are chunked, embedded, and searchable immediately.</span>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md,.markdown,application/pdf,text/plain,text/markdown"
          onChange={(event) => {
            takeFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </label>

      {error ? <div className="error-note">{error}</div> : null}

      <div className="doc-list">
        {docs.length === 0 && !uploading ? (
          <div className="empty-note">
            The library is empty. Seed documents appear on first boot, or upload your own.
          </div>
        ) : null}
        {docs.map((doc) => (
          <article key={doc.id} className="doc-row">
            <div>
              <h3>{doc.name}</h3>
              <p className="doc-meta">
                {doc.chunk_count} chunks · {formatBytes(doc.bytes_len)}
              </p>
            </div>
            <button
              type="button"
              className={`danger${pendingId === doc.id ? " confirm" : ""}`}
              onClick={() => {
                if (pendingId === doc.id) {
                  onDelete(doc.id);
                  setPendingId(null);
                } else {
                  setPendingId(doc.id);
                }
              }}
              onBlur={() => setPendingId((current) => (current === doc.id ? null : current))}
            >
              {pendingId === doc.id ? "Confirm" : "Remove"}
            </button>
          </article>
        ))}
      </div>
    </aside>
  );
}
