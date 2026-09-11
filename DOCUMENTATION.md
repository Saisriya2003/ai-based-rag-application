# AI-Based RAG Application — Complete Documentation

**AI-based Retrieval-Augmented Generation (RAG) application for document question answering**

Repository: https://github.com/Saisriya2003/ai-based-rag-application
Author: Pettem Sai Sriya · saisriyavarma@gmail.com

Resume project: *AI-Based RAG Application — Built a Retrieval-Augmented Generation system for answering questions from documents. Implemented document ingestion, embeddings, and semantic search. Integrated LLM for accurate and context-aware responses. Tech: Python, FastAPI, React, PostgreSQL.*

---

## Contents

1. [Overview](#1-overview)
2. [Tech stack](#2-tech-stack)
3. [Repository layout](#3-repository-layout)
4. [System architecture](#4-system-architecture)
5. [The RAG pipeline in depth](#5-the-rag-pipeline-in-depth)
6. [Data model and storage](#6-data-model-and-storage)
7. [Seed library](#7-seed-library)
8. [REST API reference](#8-rest-api-reference)
9. [Frontend: screens and user workflow](#9-frontend-screens-and-user-workflow)
10. [Running the application](#10-running-the-application)
11. [Configuration and modes](#11-configuration-and-modes)
12. [Testing, CI, and verification](#12-testing-ci-and-verification)
13. [Extending](#13-extending)
14. [Limitations and production path](#14-limitations-and-production-path)
15. [Glossary](#15-glossary)

---

## 1. Overview

The application answers questions **only from the documents you give it**. A user uploads PDFs, Markdown, or plain text; it extracts the text, splits it into overlapping chunks, embeds each chunk, and stores everything in a relational database. When a question arrives, it embeds the question, ranks chunks by cosine similarity, and produces an answer grounded in the top passages, with citations pointing back to document and chunk.

Design goals:

- **Zero-key demo.** Default embedding is a deterministic hashed n-gram vector; default generation is extractive. No OpenAI account or model download is required to run.
- **Honest modes.** The UI header shows *Extractive mode* or *LLM mode* based on the live `/api/health` response. Nothing is faked.
- **Swap-in production parts.** PostgreSQL via `DATABASE_URL`, MiniLM embeddings via `SENTENCE_TRANSFORMERS=1`, OpenAI generation via `OPENAI_API_KEY` — same code paths, no rewrite.
- **Grounding is visible.** Every answer shows the retrieved passages and their scores so the reader can verify it.

## 2. Tech stack

| Layer | Technology | Version (pinned) |
| --- | --- | --- |
| Language (backend) | Python | 3.11+ (CI uses 3.12) |
| Web framework | FastAPI | 0.115.6 |
| ASGI server | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy 2.0 (typed `Mapped` models) | 2.0.36 |
| Database (default) | SQLite (`backend/data/rag.db`) | built-in |
| Database (optional) | PostgreSQL via `psycopg2-binary` | 2.9.10 |
| PDF extraction | pypdf | 5.1.0 |
| Vector maths | NumPy | 2.2.1 |
| HTTP client (LLM) | httpx | 0.28.1 |
| Multipart uploads | python-multipart | 0.0.20 |
| Optional embeddings | sentence-transformers `all-MiniLM-L6-v2` | not pinned; opt-in |
| Optional LLM | OpenAI Chat Completions (`gpt-4o-mini` default) | opt-in |
| Language (frontend) | JavaScript (JSX) | — |
| UI library | React | 18 |
| Build tool | Vite | 5 |
| Styling | Hand-written CSS with design tokens; Outfit + Fraunces | — |
| Runtime (frontend) | Node.js | 18+ |
| CI | GitHub Actions (Ubuntu) | — |

## 3. Repository layout

```
ai-based-rag-application/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py      .env loader, DATABASE_URL, OPENAI_*, SENTENCE_TRANSFORMERS, mode helpers
│   │   ├── db.py          SQLAlchemy engine, Document and Chunk models, init_db, get_db
│   │   ├── ingest.py      MIME detection, text extraction, chunking, embedding, persistence
│   │   ├── embed.py       hash_embed (256-d), sentence-transformer path, cosine_similarity
│   │   ├── retrieve.py    embed query → score all chunks → top-k passages
│   │   ├── generate.py    extractive_answer, _llm_answer, answer_question with fallback
│   │   ├── seed.py        three seed documents inserted when the library is empty
│   │   └── main.py        FastAPI app, CORS, endpoints, startup seeding
│   ├── data/rag.db      SQLite database (created on first start; ignored by git except seed state)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js     port 5174, strictPort, /api → http://127.0.0.1:8002
│   └── src/
│       ├── main.jsx, App.jsx        shell, health pill, library drawer, layout
│       ├── api.js                   fetch helpers (VITE_API_URL or same-origin /api)
│       ├── index.css                design tokens and components
│       └── components/
│           ├── Chat.jsx             Ask / Passages modes, thread, citations, grounding panel
│           └── Library.jsx          document list, dropzone upload, two-step remove
├── .env.example
├── .github/workflows/ci.yml
├── start.ps1 / start.sh
├── .gitattributes, .gitignore
└── README.md
```

## 4. System architecture

```
┌──────────────────────────────┐            ┌──────────────────────────────────────────────┐
│ React UI (Vite, :5174)       │            │ FastAPI (Uvicorn, :8002)                     │
│                              │   /api/*   │                                              │
│  Library  upload / remove ───┼───────────▶│ POST /api/documents/upload ─▶ ingest_bytes   │
│  Chat     Ask / Passages ────┼───────────▶│ POST /api/ask ─▶ retrieve ─▶ answer_question │
│  Header   mode pill ◀────────┼────────────┤ GET  /api/health                             │
│  Grounding panel             │            │ GET  /api/documents  DELETE /api/documents/id│
└──────────────────────────────┘            │ POST /api/search                             │
                                            └───────────────┬──────────────────────────────┘
                                                            │ SQLAlchemy
                                            ┌───────────────▼──────────────────────────────┐
                                            │ SQLite (default)  or  PostgreSQL (DATABASE_URL)│
                                            │   documents(id, name, mime, bytes_len, created)│
                                            │   chunks(id, document_id, index, text, embedding JSON)│
                                            └──────────────────────────────────────────────┘
                              optional:  sentence-transformers (embeddings)   OpenAI API (generation)
```

## 5. The RAG pipeline in depth

### 5.1 Ingestion (`ingest.py`)

1. **MIME resolution** — by extension first (`.pdf`, `.txt`, `.md`, `.markdown`), then declared content type; `application/octet-stream` is treated as unknown and re-guessed as text.
2. **Extraction** — PDFs via `pypdf.PdfReader`, pages joined with blank lines; text decoded UTF-8 with replacement; Markdown is "softened" (headings, bold, inline code, bullets stripped) so chunks read as prose.
3. **Chunking** — `CHUNK_SIZE = 500` characters, `CHUNK_OVERLAP = 80`. Paragraphs are whitespace-normalised and joined with `\n\n`. Each window prefers to end at a sentence boundary (`. `, `? `, `! `, newline) if that boundary is past one third of the window, else at the last space. The next window starts `overlap` characters back and snaps forward to a word boundary so chunks never begin mid-word.
4. **Embedding** — each chunk → `embed_text()` → JSON-encoded list stored in `chunks.embedding`.
5. **Persistence** — one `Document` row, N `Chunk` rows in a single transaction. Errors (empty file, unsupported type, no text) surface as HTTP 400 with a clear message.

Limits: 10 MB per upload (`MAX_UPLOAD_BYTES`).

### 5.2 Embeddings (`embed.py`)

**Default: hashed n-gram embedding (256-d, offline).**

- Lower-case; replace non-alphanumerics with spaces.
- Character 3-grams and 4-grams over the compacted string, weight 1.0 each.
- Word unigrams, weight 1.6; word bigrams, weight 1.25.
- Each token string (`c3:xyz`, `w1:word`, `w2:a_b`) is SHA-256 hashed and bucketed modulo 256; the vector is L2-normalised.

Why it works for the demo: shared vocabulary and sub-word overlap between a question and its answer produce a high cosine similarity, it is deterministic, needs no model download, and embeds thousands of chunks per second. It has no semantic understanding of synonyms — see §14.

**Optional: sentence-transformers.** With `SENTENCE_TRANSFORMERS=1` and the package installed, `all-MiniLM-L6-v2` produces 384-d normalised embeddings. Because dimensions differ, re-index (delete `rag.db` or the documents) after switching.

### 5.3 Retrieval (`retrieve.py`)

- `top_k` clamped to 1–12.
- Question embedded with the same backend.
- All chunks loaded with their documents (`joinedload`), scored with cosine similarity, sorted descending, top-k returned as passages: `{chunk_id, document_id, doc, chunk_index, text, score}`.
- Brute-force scan is O(chunks); adequate for tens of thousands of chunks. See §14 for pgvector.

### 5.4 Generation (`generate.py`)

**Extractive mode (default, no key).**

1. Split each passage into sentences (regex on `.!?` followed by whitespace); drop fragments shorter than 28 characters and short colon-terminated headers.
2. Build the question term set (stop-words removed).
3. Score each sentence: `0.5 × chunk_score + 0.35 × overlap_count + 0.15 × overlap_density`; +0.18 if the question asks *how many / how much / when / who* and the sentence contains a digit.
4. Keep up to four unique sentences; supporting sentences must score at least `max(0.12, 0.5 × best)` so a distractor sharing one word is dropped. Order them with the best-matching document first, then by chunk (reading order) within each document, and join into the answer.
5. If nothing qualifies, quote the best passage verbatim (≤ 420 chars).

**LLM mode (`OPENAI_API_KEY` set).**

- Passages are numbered `[1] doc (chunk n): text`.
- System prompt: answer only from the numbered sources, cite inline like `[1]`, say clearly if the sources lack the answer, do not invent facts.
- `POST https://api.openai.com/v1/chat/completions`, model `OPENAI_MODEL`, temperature 0.2, 40 s timeout.
- Any exception (network, quota, empty response) falls back to extractive and sets `warning: "LLM unavailable (ExceptionName); used extractive answer."`, with `mode` reported as `extractive` for that response.

**Citations** — every response carries `citations[]` = `{doc, document_id, chunk_index, snippet ≤ 240 chars}` for each retrieved passage, plus the full `passages[]`.

## 6. Data model and storage

### 6.1 Tables (`db.py`)

| Table | Column | Type | Notes |
| --- | --- | --- | --- |
| `documents` | `id` | Integer PK | |
| | `name` | String(512) | original filename |
| | `mime` | String(128) | resolved MIME |
| | `bytes_len` | Integer | upload size |
| | `created_at` | DateTime | UTC, naive |
| `chunks` | `id` | Integer PK | |
| | `document_id` | Integer FK → documents.id | `ON DELETE CASCADE`, indexed |
| | `index` | Integer | position within the document |
| | `text` | Text | chunk content |
| | `embedding` | Text | JSON array of floats |

Relationship: `Document.chunks` with `cascade="all, delete-orphan"`; deleting a document removes its chunks in both SQLite and PostgreSQL. SQLite connections enable `PRAGMA foreign_keys=ON`.

### 6.2 Engine selection

`DATABASE_URL` set → PostgreSQL (`postgres://` is rewritten to `postgresql://` for SQLAlchemy). Otherwise SQLite at `backend/data/rag.db` with `check_same_thread=False`. `pool_pre_ping=True` on both. `init_db()` runs `create_all` at startup; no migration tool is needed for the two-table schema.

## 7. Seed library

Inserted by `seed.py` on first start when the library is empty:

| Document | Content | Good questions |
| --- | --- | --- |
| Aether Desk — Product Spec | owner, goals, core features, non-goals, technical notes, launch date | "What are the goals of Aether Desk?" · "When does Aether Desk launch?" → 14 October 2026 |
| Helios Labs — Time Away Policy | PTO accrual and carry-over, leave types, approvals | "How many PTO days do Helios employees receive?" → 22 days |
| Riverline — Q3 Project Brief | program, owner, problem, plan, risks | "Who owns the Riverline project?" → Ananya Rao, Operations |

The health endpoint reports `documents: 3` after seeding.

## 8. REST API reference

Base URL (dev): `http://127.0.0.1:8002`. Swagger UI at `/docs`.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/api/health` | — | `{ok, service: "ai-based-rag-application", mode: "extractive"|"llm", embedding: "hashing"|"sentence-transformers", database: "sqlite"|"postgresql", documents}` |
| GET | `/api/documents` | — | `{documents: [{id, name, mime, bytes_len, created_at, chunk_count}]}` newest first |
| POST | `/api/documents/upload` | multipart `file` (pdf/md/txt, ≤ 10 MB) | `{document: {...}}` · 400 on unsupported/empty · 413 over limit |
| DELETE | `/api/documents/{id}` | — | `{ok: true, id}` · 404 if missing |
| POST | `/api/ask` | `{question: string, top_k?: 1-12 (default 5)}` | `{answer, mode, warning, citations[], passages[]}` |
| POST | `/api/search` | `{query: string, top_k?: 1-12 (default 8)}` | `{query, passages[]}` |

Passage shape: `{chunk_id, document_id, doc, chunk_index, text, score}` where `score` is cosine similarity rounded to 4 decimals.

## 9. Frontend: screens and user workflow

### 9.1 Shell (`App.jsx`)

Two-column layout: **Library** sidebar (left) and **Chat** (right). Header shows the product name and a live mode pill (*Extractive mode* / *LLM mode*, with embedding and database in the tooltip). Under ~900 px the library collapses into a drawer opened from a header button.

### 9.2 Library (`components/Library.jsx`)

- Lists documents with name, type, size, chunk count, and relative time.
- Dropzone: drag-and-drop or click to choose; shows *Indexing…* during upload; error toast on rejection.
- *Remove* → button turns into *Confirm* (second click deletes) — prevents accidental deletion.
- Refreshes the list after upload/delete and re-fetches health so the document count stays accurate.

### 9.3 Chat (`components/Chat.jsx`)

- **Ask** mode: composer with Enter-to-send, suggested question chips for the seed library, typing indicator, assistant bubbles with the answer and **citation chips** (`doc · chunk n`); clicking a chip expands its snippet.
- **Retrieved passages** panel under each answer lists the top-k with scores; *Hide grounding / Show grounding* toggles it.
- **Passages** mode: raw semantic search — returns ranked passages without generating an answer.
- Warnings (e.g., LLM fallback) render as a subtle notice under the answer.
- Empty-library state explains how to upload.

### 9.4 Typical session

1. Open `http://localhost:5174`. Header reads *Extractive mode*; library shows three seed documents.
2. Click "How many PTO days do Helios employees receive?" → answer "22 days …" cited to the Helios policy; grounding panel shows the supporting chunk with the highest score.
3. Drop a PDF → *Indexing…* → it appears with its chunk count; ask about it immediately.
4. Switch to Passages, search a phrase, inspect scores.
5. Remove a document → Confirm → its chunks vanish from future retrieval.

## 10. Running the application

### Prerequisites

Python 3.11+, Node.js 18+, Git.

### One command

```powershell
git clone https://github.com/Saisriya2003/ai-based-rag-application.git
cd ai-based-rag-application
.\start.ps1     # Windows (or: powershell -ExecutionPolicy Bypass -File .\start.ps1)
```

```bash
git clone https://github.com/Saisriya2003/ai-based-rag-application.git
cd ai-based-rag-application
./start.sh      # macOS / Linux
```

First run creates `backend/.venv`, installs requirements and npm packages, starts both processes, and opens `http://localhost:5174`.

### Manual

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload

cd ../frontend
npm install
npm run dev     # http://localhost:5174
```

### Docker (with PostgreSQL)

`docker compose up --build` starts three containers: `db` (`postgres:16-alpine`, user/db `rag`, `pg_isready` healthcheck, persistent volume), `api` (`backend/Dockerfile`, `DATABASE_URL=postgresql://rag:rag@db:5432/rag`, waits for the healthy database, seeds on first boot), and `web` (multi-stage Node build → `nginx:alpine`, `/api/` proxied to `api:8002`, `client_max_body_size 12m` for uploads). `/api/health` then reports `"database": "postgresql"`. Host ports default to 5174/8002/5432 (`WEB_PORT`/`API_PORT`/`DB_PORT`); an `.env` beside the compose file can supply `OPENAI_API_KEY`.

### Production build

`npm run build` in `frontend/` → `dist/`. Serve statically with `/api` proxied to Uvicorn, or build with `VITE_API_URL` and add the origin to CORS in `main.py`.

## 11. Configuration and modes

Copy `.env.example` to `.env` in the repo root or `backend/` (both are searched; existing OS variables win).

| Variable | Default | Effect |
| --- | --- | --- |
| `DATABASE_URL` | empty → SQLite | e.g. `postgresql://user:pass@localhost:5432/rag` |
| `SQLITE_PATH` | `backend/data/rag.db` | Alternate SQLite file (ignored when `DATABASE_URL` is set); used by the tests |
| `OPENAI_API_KEY` | empty → extractive | Enables LLM generation |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model name |
| `SENTENCE_TRANSFORMERS` | unset → hashing | `1/true/yes` → MiniLM embeddings (`pip install sentence-transformers`) |
| `VITE_API_URL` (frontend) | empty → `/api` proxy | Absolute API base |

Mode matrix reported by `/api/health`:

| Setting | `mode` | `embedding` | `database` |
| --- | --- | --- | --- |
| none | extractive | hashing | sqlite |
| `OPENAI_API_KEY` | llm | hashing | sqlite |
| `SENTENCE_TRANSFORMERS=1` | extractive | sentence-transformers | sqlite |
| `DATABASE_URL` | extractive | hashing | postgresql |

## 12. Testing, CI, and verification

### Automated tests (`backend/tests`, pytest)

19 tests, run with `pip install -r requirements-dev.txt && python -m pytest` from `backend/`. `conftest.py` sets `SQLITE_PATH` to a temp file and blanks `DATABASE_URL`/`OPENAI_API_KEY` before any app import, so the suite never touches the real library, a developer's Postgres, or OpenAI.

- `test_ingest.py` — MIME resolution by extension; Markdown softening; single-chunk and empty inputs; on a 6,000-character document every chunk is ≤ 500 chars, is a verbatim slice starting on a word, overlaps its neighbour by at most overlap + word snap, and the tail is covered.
- `test_embed.py` — hashed embeddings are deterministic, 256-d and unit length; a question is closer to its answer passage than to an unrelated one; empty and mismatched vectors are safe.
- `test_generate.py` — numeric sentence wins for *how many*; the best-matching document leads the answer; weak distractors are dropped; empty passages message; `answer_question` reports mode and citations.
- `test_api.py` — health modes and seed count; document list; grounded ask with citations; ranked search; validation errors; upload → ask → delete round-trip with chunk cleanup; unsupported, empty, and > 10 MB uploads rejected.

### GitHub Actions (`.github/workflows/ci.yml`)

- **backend**: Python 3.12 → `pip install -r requirements-dev.txt` → `pytest` → start Uvicorn on 8002 → `GET /api/health` (triggers seeding, asserts `documents ≥ 3`) → `POST /api/ask` with a seed question → assert 200 and non-empty answer.
- **frontend**: Node 20 → `npm ci` → `npm run build`.

### End-to-end verification performed

Playwright (Edge) at 1360 px and 390 px, 8 steps: mode pill, seed library, suggested question → cited answer, grounding toggle, Passages search, upload a text file and query it, two-step remove, mobile drawer. Zero console errors, zero failed requests. Fresh clone from GitHub set up strictly by the README succeeded on Windows; CI green on Ubuntu.

## 13. Extending

- **New file types** — add extension→MIME in `EXT_MIME`, extraction branch in `extract_text()`.
- **Chunking strategy** — tune `CHUNK_SIZE`/`CHUNK_OVERLAP` or replace `chunk_text()` with a token-based splitter.
- **Other embedding models** — implement `embed_text()` for the new backend; keep vectors L2-normalised so cosine reduces to a dot product.
- **Other LLM providers** — replace `_llm_answer()` (same inputs: question + passages; return text).
- **Reranking** — insert a cross-encoder between `retrieve()` and `answer_question()`.
- **Multi-user libraries** — add `owner_id` to `documents` and filter in `retrieve()`.

## 14. Limitations and production path

- **Hash embeddings are lexical.** They reward shared words and sub-words, not meaning; synonyms and paraphrases score low. Switch to MiniLM or an API embedding for real use.
- **Brute-force retrieval** scans every chunk in Python. For > 100k chunks use PostgreSQL + `pgvector` (`embedding vector(384)` column, `<=>` cosine operator, HNSW index) — the data model already separates chunk text from embedding for this.
- **Extractive answers do not synthesise** across passages; they stitch sentences. LLM mode does the reasoning.
- **No authentication or per-user isolation** — single shared library by design for the demo.
- **Seeding and `create_all` at startup** are convenient for a demo; production would use Alembic migrations and an explicit seed command.

## 15. Glossary

- **RAG** — retrieval-augmented generation: fetch relevant text first, then answer from it.
- **Chunk** — a ~500-character slice of a document, the unit of retrieval.
- **Embedding** — a numeric vector representing text so similarity can be measured.
- **Cosine similarity** — dot product of two unit vectors; 1 means identical direction.
- **Top-k** — the k most similar chunks.
- **Extractive answer** — an answer assembled from source sentences verbatim.
- **Grounding / citation** — the passages an answer is based on, shown so it can be checked.
- **MiniLM** — a small transformer sentence-embedding model (`all-MiniLM-L6-v2`, 384-d).
- **pgvector** — PostgreSQL extension for vector columns and nearest-neighbour indexes.
