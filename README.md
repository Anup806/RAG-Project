# PDF Knowledge Assistant using RAG

A production-oriented full-stack RAG application for uploading PDF documents, asking questions, streaming grounded answers, and displaying page-level citations from retrieved chunks.

## Architecture

```mermaid
flowchart LR
  UI[React Chat UI] --> API[FastAPI REST + SSE]
  API --> PG[(PostgreSQL)]
  API --> Jobs[Background PDF Processing]
  Jobs --> PDF[PyMuPDF Extraction]
  PDF --> Clean[Text Cleaning]
  Clean --> Split[Recursive Chunking]
  Split --> Embed[Google Gemini Embedding 1]
  Embed --> Chroma[(ChromaDB)]
  API --> Hybrid[Hybrid Retrieval]
  Hybrid --> Chroma
  Hybrid --> BM25[BM25 Keyword Search]
  Hybrid --> Rerank[CrossEncoder Reranker]
  Rerank --> Gemma[Google API: Gemma 4 26B A4B]
  Gemma --> API
```

## Core Features

- Multiple PDF upload with validation and file size limits
- Background ingestion with PyMuPDF, cleaning, recursive chunking, embeddings, and Chroma persistence
- Metadata per chunk: `filename`, `document_id`, `page_number`, `chunk_id`, `text`
- Hybrid retrieval: Chroma semantic search plus BM25 keyword retrieval
- CrossEncoder reranking module, isolated for later replacement
- Top 20 retrieval candidates, best 5 context chunks sent to the LLM
- Streaming assistant responses via server-sent events
- Page-level citation display from retrieved metadata
- PostgreSQL records for users, documents, upload batches, chat sessions, and messages
- Document deletion, chat history, document filters, and document management UI

## Model Configuration

Defaults are set in `.env.example`:

```env
GOOGLE_LLM_MODEL=gemma-4-26b-a4b-it
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001
GOOGLE_EMBEDDING_DIMENSIONS=768
```

The backend uses the Google Gen AI SDK. Gemma 4 26B A4B is hosted through the Gemini API model name `gemma-4-26b-a4b-it`, and embeddings use `gemini-embedding-001`.

## Setup

1. Create your environment file:

```bash
cp .env.example .env
```

2. Set `GOOGLE_API_KEY` in `.env`.

3. Start the stack:

```bash
docker compose up --build
```

4. Open the app:

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- ChromaDB: http://localhost:8001

## Local Development

If you run the backend directly with `uvicorn`, `DATABASE_URL` must point to a Postgres server reachable from Windows, usually `localhost`:

```env
DATABASE_URL=postgresql+asyncpg://rag:rag@localhost:5432/rag
```

You can start only the database with Docker Desktop running:

```bash
docker compose up -d postgres
```

You can also use the helper script from the project root:

```powershell
.\scripts\dev-backend.ps1
```

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Use `uvicorn`, not `unicorn`. The import path is `app.main:app`.

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

For local backend development outside Docker, use a local Postgres URL and either set `CHROMA_PATH=./data/chroma` for embedded Chroma persistence or point `CHROMA_HOST` to a running Chroma service.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Google API key for Gemma generation and Gemini embeddings |
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL URL |
| `CHROMA_PATH` | Local persistent Chroma path when not using `CHROMA_HOST` |
| `CHROMA_HOST` / `CHROMA_PORT` | Optional remote Chroma service |
| `GOOGLE_LLM_MODEL` | Generation model, default `gemma-4-26b-a4b-it` |
| `GOOGLE_EMBEDDING_MODEL` | Embedding model, default `gemini-embedding-001` |
| `CHUNK_SIZE_TOKENS` | Recursive splitter target, default `700` |
| `CHUNK_OVERLAP_TOKENS` | Chunk overlap, default `120` |
| `RETRIEVAL_TOP_K` | Hybrid retrieval candidate count, default `20` |
| `RERANK_TOP_K` | Context chunks sent to the LLM, default `5` |
| `RERANKER_ENABLED` | Enables CrossEncoder reranking |
| `MAX_FILE_SIZE_MB` | Per-PDF upload limit |
| `VITE_API_URL` | Frontend API base URL |

## RAG Pipeline

1. Users upload one or more PDFs.
2. FastAPI validates MIME type, extension, and file size.
3. A background task marks the document as `processing`.
4. PyMuPDF extracts text page by page.
5. Text is normalized and split with recursive token-aware chunking.
6. Chunks are embedded with `gemini-embedding-001`.
7. Chunks and metadata are persisted in ChromaDB.
8. User questions retrieve top 20 candidates with semantic and BM25 search.
9. A CrossEncoder reranker selects the best 5 chunks.
10. Gemma answers only from those chunks.
11. The API streams tokens and returns citations from retrieved metadata.

## API Overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Database and vector store health |
| `POST` | `/api/v1/documents/upload` | Upload multiple PDFs |
| `GET` | `/api/v1/documents` | List documents |
| `GET` | `/api/v1/documents/{id}` | Get document status and metadata |
| `DELETE` | `/api/v1/documents/{id}` | Delete document, vectors, and file |
| `POST` | `/api/v1/chat/sessions` | Create chat session |
| `GET` | `/api/v1/chat/sessions` | List chat sessions |
| `PATCH` | `/api/v1/chat/sessions/{id}` | Update title or document filters |
| `DELETE` | `/api/v1/chat/sessions/{id}` | Delete chat session |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | Load message history |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | Non-streaming grounded answer |
| `POST` | `/api/v1/chat/sessions/{id}/messages/stream` | Streaming grounded answer over SSE |

## Notes For Production

- The app creates tables on startup for portfolio/development convenience. For a production deployment, add Alembic migrations and run them during release.
- Background tasks run in-process. For higher reliability, replace them with Celery, Dramatiq, or a managed queue.
- The CrossEncoder model is loaded lazily and may download weights on first use. Pre-bake the model into the backend image for locked-down production environments.
- Add authentication and per-tenant authorization before exposing multi-user deployments.
- Consider OpenSearch, Postgres full-text search, or Chroma-side sparse retrieval for larger corpora.

## Future Improvements

- Alembic migration workflow
- Object storage for PDFs
- Per-user auth with JWT/OAuth
- Ingestion retry queue and dead-letter handling
- Evaluation set for citation faithfulness and retrieval recall
- Admin dashboard for failed uploads and vector index health
