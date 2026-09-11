import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Chat from "./components/Chat.jsx";
import Library from "./components/Library.jsx";

function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [bootError, setBootError] = useState("");
  const [libError, setLibError] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [mode, setMode] = useState("ask");
  const [lastPassages, setLastPassages] = useState([]);
  const [showPassages, setShowPassages] = useState(true);

  const refresh = useCallback(async () => {
    const [nextHealth, nextDocs] = await Promise.all([api.health(), api.documents()]);
    setHealth(nextHealth);
    setDocs(nextDocs.documents || []);
    setBootError("");
  }, []);

  useEffect(() => {
    refresh().catch((error) => {
      setBootError(error.message || "Could not reach the RAG API.");
    });
  }, [refresh]);

  async function handleUpload(file) {
    setLibError("");
    setUploading(true);
    try {
      await api.upload(file);
      await refresh();
    } catch (error) {
      setLibError(error.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    setLibError("");
    try {
      await api.remove(id);
      await refresh();
    } catch (error) {
      setLibError(error.message || "Could not remove that document.");
    }
  }

  async function handleSend(text) {
    const userMessage = { id: nextId(), role: "user", text };
    const pending = { id: nextId(), role: "assistant", pending: true };
    setMessages((current) => [...current, userMessage, pending]);
    setBusy(true);
    setLibraryOpen(false);
    try {
      if (mode === "search") {
        const result = await api.search(text);
        const passages = result.passages || [];
        setLastPassages(passages);
        setMessages((current) =>
          current.map((item) =>
            item.id === pending.id
              ? {
                  id: pending.id,
                  role: "assistant",
                  kind: "search",
                  text: passages.length
                    ? `Closest ${passages.length} passages for “${text}”.`
                    : "No passages matched that query.",
                  passages,
                }
              : item
          )
        );
      } else {
        const result = await api.ask(text);
        setLastPassages(result.passages || []);
        setHealth((current) =>
          current ? { ...current, mode: result.mode || current.mode } : current
        );
        setMessages((current) =>
          current.map((item) =>
            item.id === pending.id
              ? {
                  id: pending.id,
                  role: "assistant",
                  text: result.answer,
                  citations: result.citations || [],
                  warning: result.warning,
                }
              : item
          )
        );
      }
    } catch (error) {
      setMessages((current) =>
        current.map((item) =>
          item.id === pending.id
            ? {
                id: pending.id,
                role: "assistant",
                text: error.message || "The request failed.",
                warning: "The API did not return an answer.",
              }
            : item
        )
      );
    } finally {
      setBusy(false);
    }
  }

  const modeLabel = health?.mode === "llm" ? "LLM mode" : "Extractive mode";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="mark" aria-hidden="true">
            <div className="mark-ring" />
          </div>
          <div>
            <div className="wordmark">AI-Based RAG Application</div>
            <p className="subtitle">Ask your documents. Grounded answers.</p>
          </div>
        </div>
        <div className="top-actions">
          <div className={`pill ${health?.mode === "llm" ? "llm" : "extractive"}`} title={health?.embedding || ""}>
            <span className="pill-dot" />
            {health ? modeLabel : "Connecting…"}
          </div>
          <button
            type="button"
            className="icon-btn menu-only"
            aria-label="Open library"
            onClick={() => setLibraryOpen(true)}
          >
            <svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true">
              <path d="M1 1h14M1 6h14M1 11h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </header>

      {bootError ? <div className="error-note" style={{ margin: "12px 18px 0" }}>{bootError}</div> : null}

      <div className={`backdrop${libraryOpen ? " open" : ""}`} onClick={() => setLibraryOpen(false)} />

      <main className="shell">
        <Library
          open={libraryOpen}
          docs={docs}
          uploading={uploading}
          error={libError}
          onUpload={handleUpload}
          onDelete={handleDelete}
        />
        <Chat
          mode={mode}
          onMode={setMode}
          messages={messages}
          busy={busy}
          lastPassages={lastPassages}
          showPassages={showPassages}
          onTogglePassages={() => setShowPassages((value) => !value)}
          onSend={handleSend}
        />
      </main>
    </div>
  );
}
