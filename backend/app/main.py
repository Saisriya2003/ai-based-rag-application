"""AI-Based RAG Application — API for ingest, search, and grounded answers."""

from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import (
    embedding_backend,
    database_kind,
    generation_mode,
)
from app.db import Chunk, Document, get_db, init_db
from app.generate import answer_question
from app.ingest import ingest_bytes
from app.retrieve import retrieve
from app.seed import seed_if_empty

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="AI-Based RAG Application", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskBody(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = 5


class SearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = 8


def _document_payload(doc: Document, chunk_count: int | None = None) -> dict:
    count = chunk_count
    if count is None:
        count = len(doc.chunks) if doc.chunks is not None else 0
    return {
        "id": doc.id,
        "name": doc.name,
        "mime": doc.mime,
        "bytes_len": doc.bytes_len,
        "created_at": doc.created_at.isoformat() + "Z",
        "chunk_count": count,
    }


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = next(get_db())
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    documents = db.query(Document).count()
    return {
        "ok": True,
        "service": "ai-based-rag-application",
        "mode": generation_mode(),
        "embedding": embedding_backend(),
        "database": database_kind(),
        "documents": documents,
    }


@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)) -> dict:
    counts = dict(
        db.query(Chunk.document_id, func.count(Chunk.id)).group_by(Chunk.document_id).all()
    )
    rows = db.query(Document).order_by(Document.created_at.desc()).all()
    return {"documents": [_document_payload(doc, counts.get(doc.id, 0)) for doc in rows]}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")
    try:
        document = ingest_bytes(db, file.filename or "upload", file.content_type or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"document": _document_payload(document)}


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(document)
    db.commit()
    return {"ok": True, "id": document_id}


@app.post("/api/ask")
def ask(body: AskBody, db: Session = Depends(get_db)) -> dict:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required.")
    passages = retrieve(db, question, top_k=body.top_k or 5)
    return answer_question(question, passages)


@app.post("/api/search")
def search(body: SearchBody, db: Session = Depends(get_db)) -> dict:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query is required.")
    passages = retrieve(db, query, top_k=body.top_k or 8)
    return {"query": query, "passages": passages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, reload=True)
