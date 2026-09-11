# Lumen

Ask your documents. Grounded answers.

Lumen is a retrieval-augmented generation (RAG) workspace: it indexes your files, retrieves the closest passages, and answers only from that context. Built for Pettem Sai Sriya as a production-style demo of an AI document Q&A system.

The first run needs no API keys, no Docker, and no Postgres. Three seed documents are loaded automatically so chat works immediately.

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

- **SQLite (default)** — if `DATABASE_URL` is unset, Lumen writes `backend/data/lumen.db`. Zero setup.
- **PostgreSQL** — set `DATABASE_URL` (for example `postgresql://lumen:lumen@localhost:5432/lumen`). The schema stays the same: `documents` and `chunks`.

Embeddings are stored as JSON text so both backends stay interchangeable. After you switch embedding backends, re-upload (or delete all documents and restart) so vectors share one space.

## Generation modes

| Mode | When | Behavior |
| --- | --- | --- |
| **Extractive mode** | No `OPENAI_API_KEY` | Best sentences from the top chunks, stitched into an answer. Sources listed. The UI never pretends this is a chat model. |
| **LLM mode** | `OPENAI_API_KEY` is set | OpenAI chat completion with retrieved context and citation markers. If the API call fails, Lumen falls back to extractive. |

The status pill in the header reads the `/api/health` `mode` field.

## Embeddings

- **Default (fast, offline):** character 3/4-grams plus word uni/bigrams, hashed into a 256-d vector and L2-normalized in NumPy. No model download.
- **Optional:** set `SENTENCE_TRANSFORMERS=1` to use `sentence-transformers` with `all-MiniLM-L6-v2`. Install that package yourself; it is not required for the demo.

## How to run on Windows

Use two terminals. Python 3.12 and Node 18+ are expected.

### 1. API

```bat
cd C:\Users\saisr\sriya-projects\docuqa-rag\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Health check: [http://127.0.0.1:8002/api/health](http://127.0.0.1:8002/api/health)

### 2. UI

```bat
cd C:\Users\saisr\sriya-projects\docuqa-rag\frontend
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

Serve `frontend/dist` behind a proxy that forwards `/api` to Uvicorn, or set `VITE_API_URL=http://127.0.0.1:8000` before building.

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

On first boot (empty `documents` table) Lumen indexes:

- **Aether Desk — Product Spec** — launch date, non-goals, stack
- **Helios Labs — Time Away Policy** — PTO, sick leave, parental leave
- **Riverline — Q3 Project Brief** — owner, budget, exception-time target

Try: *How many PTO days do Helios employees receive?*

## Stack

Python 3.12, FastAPI, Uvicorn, SQLAlchemy, pypdf, NumPy, React 18, Vite, PostgreSQL or SQLite.
