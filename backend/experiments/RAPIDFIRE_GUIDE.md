# RapidFire RAG Training Guide (EchoPath)

This project uses RapidFire for **offline RAG config search/evaluation**.
Production inference remains in your FastAPI app.

## 1) Create RapidFire environment (Python 3.12)

```bash
python3.12 -m venv venv_rapidfire312
./venv_rapidfire312/bin/pip install rapidfireai
./venv_rapidfire312/bin/pip install "torch<=2.8.0" "sentence-transformers>=5.1.0" "ray>=2.49.2" "transformers>=4.56.1,<5.0.0" "openai>=1.106.1" "tiktoken>=0.12.0" "langchain>=1.0.5" "langchain-classic>=1.0.0" "langchain-core>=1.0.4" "langchain-community>=0.4.1" "langchain-openai>=1.0.2" "langchain-huggingface>=1.0.0" "unstructured>=0.18.15" "numpy>=1.26.4,<2.3" datasets jupyter grpcio "mlflow>=3.2.0" "gunicorn>=23.0.0" "flask-cors>=5.0.1" loguru faiss-cpu
./venv_rapidfire312/bin/rapidfireai doctor
```

## 2) Configure model key

In project root `.env`, set at least one:

- `GEMINI_API_KEY=...` (preferred, via Gemini OpenAI-compatible endpoint)
- or `OPENAI_API_KEY=...`

Optional:

- `GEMINI_MODEL=gemini-2.0-flash`
- `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`
- `OPENAI_MODEL=gpt-4o-mini`

## 3) Build RapidFire dataset from existing alumni data

```bash
./venv/bin/python backend/data/scripts/build_rapidfire_dataset.py --limit 500
```

## 4) Run RapidFire RAG evals

```bash
./venv_rapidfire312/bin/python backend/experiments/run_rapidfire_rag_evals.py \
  --max-queries 150 \
  --num-actors 1 \
  --num-shards 2 \
  --experiment-name echopath-rag-evals
```

Results are written to:

- `rapidfire/results/echopath_rag_results.csv`

## 5) Apply best config to production

Use top run metrics (`NDCG@5`, `MRR`, `Recall`) to select:

- chunk size / overlap
- reranker top_n
- retrieval k

Then mirror those settings in:

- `backend/services/vector_store.py`
- `backend/engines/path_planner.py`
- `backend/engines/email_generator.py` (context selection policy)
