"""Extract, chunk, embed, and persist documents."""

from __future__ import annotations

import json
import re
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.db import Chunk, Document
from app.embed import embed_text

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

ALLOWED_MIME = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}

EXT_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


def guess_mime(filename: str, declared: str | None) -> str:
    name = (filename or "").lower()
    for ext, mime in EXT_MIME.items():
        if name.endswith(ext):
            return mime
    if declared and declared in ALLOWED_MIME:
        return declared
    if declared == "application/octet-stream":
        return ""
    return declared or ""


def extract_text(filename: str, mime: str, data: bytes) -> str:
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n\n".join(pages)
    text = data.decode("utf-8", errors="replace")
    if filename.lower().endswith((".md", ".markdown")) or mime in {
        "text/markdown",
        "text/x-markdown",
    }:
        text = _soften_markdown(text)
    return text


def _soften_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    return text


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    paragraphs = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n{2,}", text)]
    joined = "\n\n".join(block for block in paragraphs if block)
    if len(joined) <= size:
        return [joined]

    chunks: list[str] = []
    start = 0
    n = len(joined)
    while start < n:
        end = min(start + size, n)
        if end < n:
            window = joined[start:end]
            boundary = max(window.rfind(". "), window.rfind("? "), window.rfind("! "), window.rfind("\n"))
            if boundary >= size // 3:
                end = start + boundary + 1
            else:
                space = window.rfind(" ")
                if space >= size // 3:
                    end = start + space
        piece = joined[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
        if start < n and not joined[start].isspace() and start > 0 and not joined[start - 1].isspace():
            nxt = joined.find(" ", start, min(start + 48, n))
            if nxt != -1:
                start = nxt + 1
    return chunks


def ingest_bytes(db: Session, name: str, mime: str, data: bytes) -> Document:
    if not data:
        raise ValueError("The file is empty.")
    resolved = guess_mime(name, mime)
    if resolved not in ALLOWED_MIME and not name.lower().endswith((".pdf", ".txt", ".md", ".markdown")):
        raise ValueError("Upload a PDF, Markdown, or plain-text file.")
    if resolved not in ALLOWED_MIME:
        resolved = guess_mime(name, "text/plain") or "text/plain"

    extracted = extract_text(name, resolved, data)
    extracted = extracted.strip()
    if not extracted:
        raise ValueError("No extractable text was found in that file.")

    pieces = chunk_text(extracted)
    if not pieces:
        raise ValueError("The document produced no chunks.")

    document = Document(name=name, mime=resolved, bytes_len=len(data))
    db.add(document)
    db.flush()

    for index, piece in enumerate(pieces):
        db.add(
            Chunk(
                document_id=document.id,
                text=piece,
                index=index,
                embedding=json.dumps(embed_text(piece)),
            )
        )
    db.commit()
    db.refresh(document)
    return document
