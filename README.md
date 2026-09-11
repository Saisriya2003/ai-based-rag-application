# AI-Based RAG Application

Ask your documents. Grounded answers.

This is a retrieval-augmented generation (RAG) workspace: it indexes your files, retrieves the closest passages, and answers only from that context. Built for Pettem Sai Sriya as a production-style demo of an AI document Q&A system.

The first run needs no API keys, no Docker, and no Postgres. Three seed documents are loaded automatically so chat works immediately.

Full documentation — architecture, RAG pipeline in depth, data model, API, UI workflow, modes, configuration, CI: **[DOCUMENTATION.md](DOCUMENTATION.md)**.

[![CI](https://github.com/Saisriya2003/ai-based-rag-application/actions/workflows/ci.yml/badge.svg)](https://github.com/Saisriya2003/ai-based-rag-application/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-c9844a.svg)](LICENSE) [![Tests: pytest](https://img.shields.io/badge/tests-pytest%20%C2%B7%2019-7eb8a2.svg)](backend/tests) [![Docker Compose: PostgreSQL](https://img.shields.io/badge/docker-compose%20%C2%B7%20PostgreSQL-0c0a08.svg)](docker-compose.yml)

## Screenshots

| Ask — grounded answer with citations and retrieved passages | Passages — raw semantic search over the library |
| --- | --- |
| ![Ask mode: question, answer with citation chips, expanded snippet, retrieved passages with scores](docs/screenshots/ask.png) | ![Passages mode: ranked chunks with cosine scores for a query](docs/screenshots/passages.png) |

## Quick start

**Requirements:** [Python 3.11+](https://www.python.org/downloads/) and [Node.js 18+](https://nodejs.org/) on your PATH. No API keys, no Postgres, no Docker — SQLite and three seed documents are created on first boot.

```bash
git clone https://github.com/Saisriya2003/ai-based-rag-application.git
cd ai-based-rag-application
```

Then run the one-command starter for your OS. It installs dependencies on first run, starts the API on `http://127.0.0.1:8002` and the UI on `http://localhost:5174`, and opens the browser.

| OS | Command |
| --- | --- |
| Windows (PowerShell) | `.\start.ps1` |
| macOS / Linux | `chmod +x start.sh && ./start.sh` |

If PowerShell refuses to run the script ("running scripts is disabled"), use:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Manual steps are under **How to run on Windows** below (the same commands work on macOS/Linux with `python3` and `source .venv/bin/activate`). CI runs the install, an API smoke test, and the production build on every push.

### Troubleshooting

- **`python` not found** — on macOS/Linux use `python3`; on Windows install from python.org and tick "Add to PATH".
- **`psycopg2` fails to install** — only needed for PostgreSQL. Remove that line from `backend/requirements.txt` if you are staying on SQLite.
- **Port 8002 or 5174 already in use** — change the port in `start.ps1` / `start.sh` and `frontend/vite.config.js` together.
- **"Could not reach the RAG API"** — the backend is not up yet. Check `http://127.0.0.1:8002/api/health`.

| | |
| --- | --- |
| Stack | Python, FastAPI, SQLAlchemy, React, Vite |
| Database | SQLite by default; PostgreSQL via `DATABASE_URL` |
| Pipeline | Ingest (PDF/MD/TXT) → chunk → embed → cosine retrieval → answer with citations |
| Generation | Extractive offline; OpenAI when `OPENAI_API_KEY` is set |

## What this demonstrates

- Document ingestion, chunking, and an embedding pipeline
- Semantic search over stored chunks
- Context-aware answers with source citations back to the document
- One schema that runs on SQLite locally and PostgreSQL in production

## Architecture

```
ingest → embed → retrieve → generate
```

1. **Ingest** — PDF, Markdown, or text is extracted (`pypdf` for PDFs), then split into ~500-character chunks with 80-character overlap.
2. **Embed** — Each chunk becomes a dense vector and is stored on the `chunks` table.
3. **Retrieve** — The question is embedded the same way. Cosine similarity ranks chunks; the top-k passages are returned.
4. **Generate** — Those passages become the only allowed context for an answer, with citations back to document name and chunk index.

```
Upload / seed docs
        │
        ▼
   extract text ──► chunk ──► embed ──► documents + chunks (Postgres or SQLite)
                                              │
Question ──► embed ──► cosine top-k ──────────┘
                                              │
                                              ▼
                                    generate (extractive or LLM)
                                              │
                                              ▼
                                    answer + source chips
```

## Postgres vs SQLite

`backend/app/db.py` picks the engine from the environment.

- **SQLite (default)** — if `DATABASE_URL` is unset, the API writes `backend/data/rag.db`. Zero setup.
- **PostgreSQL** — set `DATABASE_URL` (for example `postgresql://rag:rag@localhost:5432/rag`). The schema stays the same: `documents` and `chunks`.

Embeddings are stored as JSON text so both backends stay interchangeable. After you switch embedding backends, re-upload (or delete all documents and restart) so vectors share one space.

## Generation modes

| Mode | When | Behavior |
| --- | --- | --- |
| **Extractive mode** | No `OPENAI_API_KEY` | Best sentences from the top chunks, stitched into an answer. Sources listed. The UI never pretends this is a chat model. |
| **LLM mode** | `OPENAI_API_KEY` is set | OpenAI chat completion with retrieved context and citation markers. If the API call fails, the app falls back to extractive. |

The status pill in the header reads the `/api/health` `mode` field.

## Embeddings

- **Default (fast, offline):** character 3/4-grams plus word uni/bigrams, hashed into a 256-d vector and L2-normalized in NumPy. No model download.
- **Optional:** set `SENTENCE_TRANSFORMERS=1` to use `sentence-transformers` with `all-MiniLM-L6-v2`. Install that package yourself; it is not required for the demo.

## How to run on Windows

Use two terminals. Python 3.12 and Node 18+ are expected.

### 1. API

```bat
cd C:\Users\saisr\sriya-projects\ai-based-rag-application\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Health check: [http://127.0.0.1:8002/api/health](http://127.0.0.1:8002/api/health)

### 2. UI

```bat
cd C:\Users\saisr\sriya-projects\ai-based-rag-application\frontend
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174). Vite proxies `/api` to port 8002.

Optional keys go in a `.env` at the repo root (see `.env.example`):

```
DATABASE_URL=
OPENAI_API_KEY=
SENTENCE_TRANSFORMERS=0
```

### Production build

```bat
cd frontend
npm run build
```

Serve `frontend/dist` behind a proxy that forwards `/api` to Uvicorn, or set `VITE_API_URL=http://127.0.0.1:8002` before building.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Mode, embedding backend, database, document count |
| GET | `/api/documents` | Library |
| POST | `/api/documents/upload` | Multipart file ingest |
| DELETE | `/api/documents/{id}` | Remove a document and its chunks |
| POST | `/api/ask` | `{ question, top_k? }` → answer + citations + passages |
| POST | `/api/search` | `{ query }` → raw semantic hits, no generation |

## Seed library

On first boot (empty `documents` table) the app indexes:

- **Aether Desk — Product Spec** — launch date, non-goals, stack
- **Helios Labs — Time Away Policy** — PTO, sick leave, parental leave
- **Riverline — Q3 Project Brief** — owner, budget, exception-time target

Try: *How many PTO days do Helios employees receive?*

## Stack

Python 3.12, FastAPI, Uvicorn, SQLAlchemy, pypdf, NumPy, React 18, Vite, PostgreSQL or SQLite.

## Run with Docker

Three containers: **PostgreSQL 16**, the FastAPI RAG service pointed at it via `DATABASE_URL`, and nginx serving the built React UI with `/api` proxied. This is the production shape from the resume line (Python, FastAPI, React, PostgreSQL) — `/api/health` reports `"database": "postgresql"`.

```bash
docker compose up --build
# UI  http://localhost:5174        API  http://localhost:8002/api/health
```

Put `OPENAI_API_KEY=...` in a `.env` file beside `docker-compose.yml` to enable LLM mode inside the container. Change host ports with `WEB_PORT` / `API_PORT` / `DB_PORT`. Stop with `docker compose down` (add `-v` to drop the Postgres volume).

## Tests

`backend/tests` — 19 pytest tests on an **isolated SQLite file** (the real library is never touched): boundary-aware chunking with overlap and full coverage, deterministic unit-length hashed embeddings, extractive answer ranking (numeric sentences for *how many*, best document first, weak distractors dropped), and the full API: seeding, ask with citations, ranked search, upload → ask → delete, and validation errors (unsupported, empty, oversized files).

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## License

MIT — see [LICENSE](LICENSE). Seed documents are fictional.