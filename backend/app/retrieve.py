"""Embed a query and return the top-k chunks by cosine similarity."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session, joinedload

from app.db import Chunk
from app.embed import cosine_similarity, embed_text


def retrieve(db: Session, query: str, top_k: int = 5) -> list[dict]:
    question = (query or "").strip()
    if not question:
        return []
    k = max(1, min(int(top_k or 5), 12))
    qvec = embed_text(question)

    rows = db.query(Chunk).options(joinedload(Chunk.document)).all()
    scored: list[tuple[float, Chunk]] = []
    for chunk in rows:
        try:
            vector = json.loads(chunk.embedding)
        except (TypeError, json.JSONDecodeError):
            continue
        score = cosine_similarity(qvec, vector)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    passages: list[dict] = []
    for score, chunk in scored[:k]:
        passages.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "doc": chunk.document.name if chunk.document else "Untitled",
                "chunk_index": chunk.index,
                "text": chunk.text,
                "score": round(float(score), 4),
            }
        )
    return passages
