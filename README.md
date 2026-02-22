# EchoPath Quick Start

This setup gets you to a usable local product with:
- FastAPI backend (`http://127.0.0.1:8000`)
- Next.js frontend (`http://localhost:3000`)
- Optional pgvector retrieval for RAG

## 1) Configure environment

Copy the example file and fill your real keys:

```bash
cp .env.example .env
```

Required for LLM generation:
- `GEMINI_API_KEY`
- `RAPIDFIRE_API_KEY` + `RAPIDFIRE_BASE_URL` (if using Rapidfire endpoint)
- `OPENAI_API_KEY` (optional fallback)

Recommended provider order:

```env
LLM_PROVIDER_ORDER=rapidfire,gemini,openai
```

For RAG embeddings (auto-selects provider by available key):

```env
EMBEDDING_PROVIDER=auto
# OpenAI: text-embedding-3-small
# Gemini: text-embedding-004
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

## 2) Start pgvector (for production-style RAG)

```bash
docker compose -f docker-compose.pgvector.yml up -d
```

Set:

```env
PG_DSN=postgresql://echopath:echopath@localhost:5432/echopath
```

## 3) Build RAG index

```bash
./venv/bin/python backend/data/scripts/build_rag_index.py
```

## 4) Start backend

```bash
./venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 5) Start frontend

```bash
cd frontend
npm run dev
```

If needed, set API URL:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## 6) Smoke test APIs

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/student/analyze \
  -H "Content-Type: application/json" \
  -d '{"fips_code":"06099","current_education":"Community College","target_function":"Marketing","target_level":"Manager"}'
```

## Runtime behavior

- Email generation: Rapidfire -> Gemini -> OpenAI -> template fallback
- Path planning: Rapidfire planner + RAG evidence -> deterministic fallback
- RAG retrieval: enabled only when `PG_DSN` is configured and pgvector is reachable
