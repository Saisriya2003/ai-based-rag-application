import { useEffect, useRef, useState } from "react";

const SUGGESTIONS = [
  "How many PTO days do Helios employees receive?",
  "When does Aether Desk launch, and what is out of scope?",
  "Who owns Riverline, and what is the exception-handling target?",
];

function Citations({ citations }) {
  const [open, setOpen] = useState(null);
  if (!citations?.length) return null;
  const active = open === null ? null : citations[open];
  return (
    <>
      <div className="chips">
        {citations.map((citation, index) => (
          <button
            key={`${citation.doc}-${citation.chunk_index}-${index}`}
            type="button"
            className={`chip${open === index ? " open" : ""}`}
            onClick={() => setOpen((current) => (current === index ? null : index))}
            aria-expanded={open === index}
          >
            {citation.doc} · {citation.chunk_index}
          </button>
        ))}
      </div>
      {active ? <div className="snippet">{active.snippet}</div> : null}
    </>
  );
}

function Message({ item }) {
  if (item.role === "user") {
    return (
      <article className="bubble user">
        <div className="who">You</div>
        <div className="bubble-body">
          <p>{item.text}</p>
        </div>
      </article>
    );
  }

  if (item.pending) {
    return (
      <article className="bubble assistant" aria-live="polite">
        <div className="who">Assistant</div>
        <div className="bubble-body">
          <div className="typing" aria-label="Thinking">
            <i />
            <i />
            <i />
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="bubble assistant">
      <div className="who">{item.kind === "search" ? "Passages" : "Assistant"}</div>
      <div className="bubble-body">
        {item.text ? <p>{item.text}</p> : null}
        {item.kind === "search" && item.passages?.length
          ? item.passages.map((passage) => (
              <div className="passage" key={`${passage.document_id}-${passage.chunk_index}`}>
                <h4>
                  {passage.doc}
                  <span className="score">{passage.score.toFixed(3)}</span>
                </h4>
                <p>{passage.text}</p>
              </div>
            ))
          : null}
        {item.warning ? <div className="warning">{item.warning}</div> : null}
        <Citations citations={item.citations} />
      </div>
    </article>
  );
}

export default function Chat({
  mode,
  onMode,
  messages,
  busy,
  lastPassages,
  onSend,
  showPassages,
  onTogglePassages,
}) {
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);
  const areaRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, lastPassages]);

  useEffect(() => {
    const node = areaRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(node.scrollHeight, 140)}px`;
  }, [draft]);

  function submit(text) {
    const value = (text ?? draft).trim();
    if (!value || busy) return;
    onSend(value);
    setDraft("");
  }

  return (
    <section className="workspace">
      <div className="workspace-head">
        <div className="mode-switch" role="tablist" aria-label="Query mode">
          <button type="button" className={mode === "ask" ? "on" : ""} onClick={() => onMode("ask")}>
            Ask
          </button>
          <button
            type="button"
            className={mode === "search" ? "on" : ""}
            onClick={() => onMode("search")}
          >
            Passages
          </button>
        </div>
        <button type="button" className="ghost" onClick={onTogglePassages}>
          {showPassages ? "Hide grounding" : "Show grounding"}
        </button>
      </div>

      <div className="thread">
        {messages.length === 0 ? (
          <div className="hero-empty">
            <h2>Ask your documents. Grounded answers.</h2>
            <p>
              The app retrieves the most relevant passages from your library, then answers
              only from those passages — so every claim can be traced to a source.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((question) => (
                <button key={question} type="button" onClick={() => submit(question)}>
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((item) => <Message key={item.id} item={item} />)
        )}
        <div ref={endRef} />
      </div>

      {showPassages && lastPassages.length > 0 ? (
        <details className="passages" open>
          <summary>Retrieved passages · {lastPassages.length}</summary>
          {lastPassages.map((passage) => (
            <div className="passage" key={`${passage.chunk_id}-${passage.chunk_index}`}>
              <h4>
                {passage.doc} · chunk {passage.chunk_index}
                <span className="score">{passage.score.toFixed(3)}</span>
              </h4>
              <p>{passage.text}</p>
            </div>
          ))}
        </details>
      ) : null}

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="composer-box">
          <textarea
            ref={areaRef}
            rows={1}
            value={draft}
            placeholder={mode === "search" ? "Search passages…" : "Ask a question about the library…"}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
          />
          <button type="submit" className="primary" disabled={busy || !draft.trim()}>
            {mode === "search" ? "Search" : "Ask"}
          </button>
        </div>
      </form>
    </section>
  );
}
