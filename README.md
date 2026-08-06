# Enterprise Multimodal RAG

A production-oriented **Retrieval-Augmented Generation (RAG)** system that ingests enterprise documents, indexes them for hybrid search, and answers questions with cited, LLM-generated responses. It supports **text, tables, images, and charts** across common office formats.

## What It Does

1. **Upload** PDF, DOCX, PPTX, Excel, images, and plain text
2. **Parse & structure** content (headings, sections, captions, table/image context)
3. **Chunk & embed** text, tables, and images into [Qdrant](https://qdrant.tech/) vector collections
4. **Retrieve** with hybrid BM25 + dense search, optional BGE reranking, and query-aware boosting
5. **Generate** answers via OpenRouter (e.g. Claude), with citations, confidence scores, and hallucination checks
6. **Chat** through a built-in web UI or REST API

## Architecture




<img width="1536" height="1024" alt="chatbotarch" src="https://github.com/user-attachments/assets/9529053f-d7d6-48ba-a812-8a2b30e652f1" />



## Key Features

| Area | Details |
|------|---------|
| **Formats** | PDF, DOCX, PPTX, XLS/XLSX, images (PNG, JPG, etc.), TXT/MD |
| **Multimodal** | Separate collections for text, tables, images, and multimodal chunks |
| **Retrieval** | Dense (BGE), BM25, hybrid fusion, parent-child chunks, multimodal retrieval |
| **Reranking** | BGE cross-encoder reranker (`RERANK_TOP_K` results) |
| **LLM** | OpenRouter API (configurable model) |
| **Quality** | Citation builder, hallucination checker, confidence scoring |
| **UI** | Simple web interface at `/` for upload, document list, and chat |

## Tech Stack

- **API:** FastAPI + Uvicorn
- **Vector DB:** Qdrant (Docker)
- **Relational DB:** PostgreSQL + SQLAlchemy + Alembic
- **Cache:** Redis
- **Auth:** JWT (python-jose) + bcrypt passwords
- **Embeddings:** `sentence-transformers` (BGE-small for text, CLIP for images)
- **Search:** `rank-bm25` + dense vector search (tenant-scoped hybrid)
- **LLM:** OpenRouter (OpenAI-compatible client)
- **Parsing:** PyMuPDF, pdfplumber, python-docx, python-pptx, optional Docling/Unstructured/OCR

## Project Structure

```
EnterpriseRag/
├── main.py                 # FastAPI app entry point
├── docker-compose.yml      # Qdrant, PostgreSQL, Redis
├── requirements.txt
├── static/index.html       # Web UI
├── app/
│   ├── api/                # REST endpoints (auth, upload, chat, search, documents, tenants)
│   ├── auth/               # JWT security and FastAPI dependencies
│   ├── db/                 # SQLAlchemy models and session
│   ├── cache/              # Redis client
│   ├── services/           # Document and tenant business logic
│   ├── workflows/          # End-to-end pipelines (ingestion, indexing, retrieval, chat)
│   ├── ingestion/          # Loaders, parsers, content extractors
│   ├── document_structure/ # Headings, sections, caption/context linking
│   ├── chunking/           # Semantic, section, parent-child, multimodal chunkers
│   ├── embeddings/         # Text, image, table embedding
│   ├── vectorstore/        # Qdrant client, collections, indexing
│   ├── retrieval/          # BM25, dense, hybrid, parent, multimodal search
│   ├── reranking/          # BGE reranker pipeline
│   ├── context_builder/    # Context assembly and token optimization
│   ├── llm/                # Prompts, response generation, citations
│   └── models/             # Pydantic data models
└── data/                   # Raw uploads, processed data, chunks (created at runtime)
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker (for Qdrant)
- OpenRouter API key

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts **Qdrant**, **PostgreSQL** (host port **5433**), **Redis**, and **MinIO** (ports **9000** API, **9001** console).

> **Windows note:** If you have a local PostgreSQL on port 5432, the Docker Postgres uses **5433** to avoid conflicts. Set `DATABASE_URL=postgresql://rag:rag@127.0.0.1:5433/enterprise_rag`.

### 2b. Start Celery worker + Flower (Phase 2 — required for uploads)

In a **second terminal** (same conda env):

```bash
# Windows
scripts\run_worker.bat

# Linux / macOS
./scripts/run_worker.sh
```

Or via Docker (includes worker + Flower):

```bash
docker compose --profile workers up -d
```

- **Flower** (task monitor): http://localhost:5555
- **MinIO console**: http://localhost:9001 (user/pass: `minioadmin`)

Set `CELERY_ENABLED=false` in `.env` to fall back to in-process background tasks (Phase 1 behavior).

### 2c. Start Prometheus + Grafana (Phase 3 — optional monitoring)

```bash
docker compose --profile monitoring up -d
```

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin / admin)
- **App metrics**: http://localhost:8000/metrics (run `python main.py` on the host)

Set `QUOTAS_ENABLED=false` to disable upload/chat/search limits during local dev.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env` and set at minimum:

```env
DATABASE_URL=postgresql://rag:rag@localhost:5432/enterprise_rag
REDIS_URL=redis://localhost:6379/0
CELERY_ENABLED=true
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
USE_MINIO=true
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=enterprise-rag
SECRET_KEY=your-random-secret-key
QDRANT_URL=http://localhost:6333
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=anthropic/claude-3-haiku:beta
TEXT_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

Set `REQUIRE_AUTH=false` only for local development without login.

### 5. Run database migrations (optional — tables also auto-create on startup)

```bash
alembic upgrade head
```

### 6. Run the server

```bash
python main.py
```

- **Web UI:** http://localhost:8000  
- **API docs:** http://localhost:8000/docs  

On startup, the app initializes PostgreSQL tables, connects to Redis, initializes Qdrant collections, and restores indexed documents.

### 7. Register and use the API

1. Open http://localhost:8000 and **register** a new organization (creates tenant + admin user)
2. Or call `POST /api/v1/auth/register` then use the returned JWT as `Authorization: Bearer <token>`
3. All upload, chat, search, and document endpoints require authentication (unless `REQUIRE_AUTH=false`)

Heavy parsers (Docling, Unstructured, OCR) are **off by default** for faster CPU uploads. Enable them in `.env` when needed.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Register tenant + admin user |
| `POST` | `/api/v1/auth/login` | No | Login (form: username=email, password) |
| `GET` | `/api/v1/auth/me` | Yes | Current user profile |
| `GET` | `/api/v1/tenants/me` | Yes | Current tenant (Redis-cached) |
| `PATCH` | `/api/v1/tenants/me` | Admin | Update tenant settings |
| `POST` | `/api/v1/api-keys` | Admin | Create tenant API key (shown once) |
| `GET` | `/api/v1/api-keys` | Admin | List API key prefixes |
| `POST` | `/api/v1/upload` | Yes | Upload a document (background processing) |
| `GET` | `/api/v1/upload/status/{document_id}` | Yes | Check ingestion/indexing status |
| `GET` | `/api/v1/documents` | Yes | List tenant documents |
| `DELETE` | `/api/v1/documents/{document_id}` | Yes | Remove a document |
| `POST` | `/api/v1/chat` | Yes | RAG chat with citations |
| `POST` | `/api/v1/chat/stream` | Yes | Streaming chat |
| `POST` | `/api/v1/search` | Yes | Search chunks without LLM |
| `POST` | `/api/v1/search/similar` | Yes | Similarity search |
| `DELETE` | `/api/v1/api-keys/{key_id}` | Admin | Revoke API key |
| `GET` | `/api/v1/tenants/me/usage` | Yes | Usage vs plan limits |
| `GET` | `/api/v1/plans` | Admin | List plan tiers and limits |
| `GET` | `/api/v1/audit-logs` | Admin | Tenant audit trail (paginated) |
| `GET` | `/api/v1/cache/test` | Yes | Verify Redis read/write |
| `GET` | `/api/v1/health` | No | Health check (Qdrant, Redis, LLM) |
| `GET` | `/metrics` | No | Prometheus metrics (when enabled) |
| `POST` | `/api/v1/agent/chat` | Yes | Agentic multi-step chat (LangChain tools) |
| `POST` | `/api/v1/agent/session` | Yes | Create new agent session ID |
| `DELETE` | `/api/v1/agent/session/{session_id}` | Yes | Clear agent session memory |

## Configuration Highlights

| Variable | Default | Purpose |
|----------|---------|---------|
| `RETRIEVAL_METHOD` | `hybrid` | `dense`, `bm25`, or `hybrid` |
| `TOP_K` | `8` | Chunks retrieved before reranking |
| `RERANK_TOP_K` | `5` | Chunks kept after reranking |
| `CHUNK_SIZE` | `1024` | Child chunk size |
| `PARENT_CHUNK_SIZE` | `2048` | Parent chunk size |
| `USE_DOCLING` | `false` | Advanced PDF/layout parsing |
| `ENABLE_OCR` | `false` | OCR for scanned content |
| `USE_LLM_ENRICHMENT` | `false` | LLM-based table/image enrichment |
| `QUOTAS_ENABLED` | `true` | Enforce per-tenant plan limits |
| `PROMETHEUS_ENABLED` | `true` | Expose `/metrics` for Prometheus |
| `AGENT_ENABLED` | `true` | Enable `/api/v1/agent/chat` and UI agent mode |
| `AGENT_MAX_ITERATIONS` | `5` | Max tool-calling steps per agent request |
| `AGENT_MEMORY_TURNS` | `10` | Redis conversation turns per agent session |

### Agent tools (Phase 4)

| Tool | Purpose |
|------|---------|
| `search_documents` | Hybrid search over tenant chunks |
| `answer_with_rag` | Full RAG Q&A with citations |
| `list_documents` | List tenant documents and status |
| `summarize_document` | Summarize one or all documents |
| `document_status` | Check processing status by document ID |

Toggle **Agent mode** in the Web UI or call `POST /api/v1/agent/chat` directly.

### Plan tiers (Phase 3)

| Plan | Documents | Storage | Chat/month | Search/month |
|------|-----------|---------|------------|--------------|
| free | 10 | 100 MB | 500 | 1,000 |
| pro | 100 | 5 GB | 10,000 | 20,000 |
| enterprise | 10,000 | 100 GB | 1,000,000 | 1,000,000 |

Upgrade via `PATCH /api/v1/tenants/me` with `{ "plan": "pro" }` (admin).

## Operations Runbook

Daily commands for running, verifying, and resetting the app. Examples use **Windows CMD**; on Linux/macOS replace `scripts\run_worker.bat` with `./scripts/run_worker.sh` and `%TOKEN%` with `$TOKEN`.

### URLs

| What | URL |
|------|-----|
| Web UI | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health |
| Prometheus metrics | http://localhost:8000/metrics |
| MinIO console | http://localhost:9001 (`minioadmin` / `minioadmin`) |
| Flower (workers profile) | http://localhost:5555 |

Protected endpoints (usage, audit, documents) **do not work** in the browser address bar — use curl or Swagger with a Bearer token.

### Every time you run the app (3 terminals)

**Terminal 1 — Docker**

```cmd
cd C:\Users\ASHISH\Downloads\EnterpriseRag\EnterpriseRag
docker compose up -d
```

**Terminal 2 — Celery worker (required for uploads)**

```cmd
cd C:\Users\ASHISH\Downloads\EnterpriseRag\EnterpriseRag
conda activate ent
scripts\run_worker.bat
```

**Terminal 3 — FastAPI app**

```cmd
cd C:\Users\ASHISH\Downloads\EnterpriseRag\EnterpriseRag
conda activate ent
python main.py
```

Wait for `Uvicorn running on http://0.0.0.0:8000`, then open http://localhost:8000.

### Fresh setup (wipe all data)

> **Warning:** Deletes all tenants, users, documents, vectors, and MinIO files permanently.

```cmd
cd C:\Users\ASHISH\Downloads\EnterpriseRag\EnterpriseRag
docker compose down -v
docker compose up -d
conda activate ent
alembic upgrade head
```

Then start worker + app, register once at http://localhost:8000.

Verify clean slate:

```cmd
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT COUNT(*) FROM users;"
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT COUNT(*) FROM tenants;"
```

Both should show `1` after a single registration.

### Alembic: tables already exist but migration fails

If `alembic upgrade head` errors with `relation "tenants" already exists` (tables created by `init_db()` on startup):

```cmd
alembic stamp 002_api_keys
alembic upgrade head
```

### Login and JWT token (CMD)

**Login** (`username` = email, not client_id):

```cmd
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=YOUR_EMAIL&password=YOUR_PASSWORD"
```

Copy `access_token` from the JSON response, then:

```cmd
set TOKEN=eyJhbGciOiJIUzI1NiIs...paste_full_token_here
```

`set TOKEN` only works in the **same** CMD window. Do not include `Bearer` in the variable.

### Phase 3 — verify usage, documents, audit (CMD)

```cmd
curl -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/v1/tenants/me/usage
curl -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/v1/documents
curl -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/v1/audit-logs
```

**Pass:** usage shows `plan`, counters, and `limits`; documents show `status: completed`; audit shows `register`, `login`, `upload`, `chat`.

One-liner without `set TOKEN`:

```cmd
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://localhost:8000/api/v1/tenants/me/usage
```

### Public health check (no token)

```cmd
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/metrics
```

**Pass:** health returns `"status": "healthy"`, `"version": "1.3.0"`, `"quotas": "enabled"`.

### Count admins and users (PostgreSQL)

```cmd
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT role, COUNT(*) AS count FROM users GROUP BY role ORDER BY role;"
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT COUNT(*) AS total_users FROM users;"
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT COUNT(*) AS tenants FROM tenants;"
```

List users with email and role:

```cmd
docker exec enterprise-rag-postgres psql -U rag -d enterprise_rag -c "SELECT email, role, created_at FROM users ORDER BY created_at;"
```

Each **register** creates **1 tenant + 1 admin** user. There is no cross-tenant super-admin in Phase 3.

### Quick “app is working” checklist

| Step | Action | Pass |
|------|--------|------|
| 1 | http://localhost:8000 loads | Login/register page |
| 2 | `curl http://localhost:8000/api/v1/health` | `"healthy"` |
| 3 | Register + login in UI | Main app loads |
| 4 | Upload PDF/DOCX | Status → `completed` |
| 5 | Chat about the document | Answer returned |
| 6 | `curl .../tenants/me/usage` with token | Counters match activity |

### Common issues

| Problem | Fix |
|---------|-----|
| `Could not connect to localhost:8000` | Start `python main.py` |
| Upload stuck on `processing` | Start `scripts\run_worker.bat` |
| `Not authenticated` on usage/audit | Use `Authorization: Bearer` header; browser URL alone is not enough |
| Login 500 after Phase 3 | `pip install "prometheus-fastapi-instrumentator>=8.0.1"` and restart app |
| `alembic` duplicate table error | `alembic stamp 002_api_keys` then `alembic upgrade head` |
| Postgres connection refused | `docker compose up -d` |

### Agent chat (Phase 4)

```cmd
curl -X POST http://localhost:8000/api/v1/agent/chat -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"query\":\"List my documents and summarize the latest one\",\"use_memory\":true}"
```

**Pass:** JSON with `answer`, `tools_used` (e.g. `list_documents`, `summarize_document`), and `session_id`.

### Run tests

```cmd
conda activate ent
pytest tests/test_phase3.py tests/test_phase4.py tests/test_tenant_isolation.py -q
```

## Pipelines (Summary)

- **Ingestion** — Load file → parse layout → detect structure → link tables/images → build metadata
- **Indexing** — Chunk (semantic/section/parent-child) → embed → store in Qdrant + BM25
- **Retrieval** — Hybrid search → query boosting → optional rerank → assemble context within token budget
- **Chat** — Retrieve → generate answer → attach citations → hallucination check → return sources

## License

Add your license here if applicable.
