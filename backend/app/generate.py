"""Answer a question from retrieved passages — LLM when keyed, else extractive."""

from __future__ import annotations

import re

import httpx

from app.config import OPENAI_API_KEY, OPENAI_MODEL, generation_mode

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}


def _citations(passages: list[dict]) -> list[dict]:
    citations = []
    for item in passages:
        snippet = " ".join(item["text"].split())
        if len(snippet) > 240:
            snippet = snippet[:237].rstrip() + "…"
        citations.append(
            {
                "doc": item["doc"],
                "document_id": item.get("document_id"),
                "chunk_index": item["chunk_index"],
                "snippet": snippet,
            }
        )
    return citations


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 1}


def _sentences(text: str) -> list[str]:
    parts: list[str] = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        if re.search(r"[.!?]", para):
            parts.extend(_SENTENCE_SPLIT.split(para))
        elif len(para) > 40:
            parts.append(para)
    clean: list[str] = []
    for part in parts:
        piece = " ".join(part.split())
        if len(piece) < 28:
            continue
        if piece.endswith(":") and len(piece) < 48:
            continue
        clean.append(piece)
    return clean


def extractive_answer(question: str, passages: list[dict]) -> str:
    if not passages:
        return (
            "No indexed passages were available. Upload a document or wait for the "
            "library to finish seeding, then ask again."
        )

    q_terms = _terms(question)
    ranked: list[tuple[float, int, int, str]] = []
    for passage in passages:
        chunk_score = float(passage.get("score") or 0)
        for sentence in _sentences(passage["text"]):
            words = _terms(sentence)
            if not words:
                continue
            overlap = len(words & q_terms)
            density = overlap / max(len(words), 1)
            score = chunk_score * 0.5 + overlap * 0.35 + density * 0.15
            qlow = question.lower()
            if re.search(r"\b(how many|how much|when|who)\b", qlow) and re.search(r"\d", sentence):
                score += 0.18
            ranked.append((score, passage.get("document_id") or 0, passage["chunk_index"], sentence))

    ranked.sort(key=lambda row: row[0], reverse=True)
    best_score = ranked[0][0] if ranked else 0.0
    # Supporting sentences must be reasonably close to the best match, so a
    # distractor that merely shares a word does not pad the answer.
    floor = max(0.12, best_score * 0.5)
    chosen: list[tuple[float, int, int, str]] = []
    seen: set[str] = set()
    for score, doc_id, index, sentence in ranked:
        key = sentence.lower()
        if key in seen:
            continue
        if chosen and score < floor:
            continue
        seen.add(key)
        chosen.append((score, doc_id, index, sentence))
        if len(chosen) >= 4:
            break

    if not chosen:
        best = passages[0]
        quote = " ".join(best["text"].split())
        if len(quote) > 420:
            quote = quote[:417].rstrip() + "…"
        return f"Closest passage from {best['doc']}:\n\n“{quote}”"

    # Lead with the best-matching document, then keep reading order inside each
    # document. `chosen` is in score order, so first appearance = best document.
    doc_rank: dict[int, int] = {}
    for _, doc_id, _, _ in chosen:
        doc_rank.setdefault(doc_id, len(doc_rank))
    chosen.sort(key=lambda row: (doc_rank[row[1]], row[2]))
    body = " ".join(sentence for _, _, _, sentence in chosen)
    return body


def _llm_answer(question: str, passages: list[dict]) -> str:
    blocks = []
    for i, passage in enumerate(passages, start=1):
        blocks.append(f"[{i}] {passage['doc']} (chunk {passage['chunk_index']}):\n{passage['text']}")
    context = "\n\n".join(blocks) if blocks else "(no passages retrieved)"
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Lumen, a retrieval-augmented assistant. Answer only from "
                    "the numbered sources. Cite them inline like [1]. If the sources "
                    "do not contain the answer, say so clearly. Do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": f"Sources:\n{context}\n\nQuestion: {question}",
            },
        ],
    }
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=40.0,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"].strip()
    if not text:
        raise RuntimeError("Empty model response")
    return text


def answer_question(question: str, passages: list[dict]) -> dict:
    mode = generation_mode()
    warning = None
    if mode == "llm":
        try:
            text = _llm_answer(question, passages)
        except Exception as exc:  # noqa: BLE001 — demo must still answer
            text = extractive_answer(question, passages)
            mode = "extractive"
            warning = f"LLM unavailable ({exc.__class__.__name__}); used extractive answer."
    else:
        text = extractive_answer(question, passages)

    return {
        "answer": text,
        "mode": mode,
        "warning": warning,
        "citations": _citations(passages),
        "passages": passages,
    }
