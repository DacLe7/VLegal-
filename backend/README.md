# V-Legal Backend

FastAPI backend for the V-Legal RAG demo. This backend is RAG only, not GraphRAG.

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
python scripts/ingest_data.py --reset
python -m app.main
```

Set `GEMINI_API_KEY` in your local `.env` or in your deployment environment. Do not commit `.env` or any real API key.

Recommended demo chunk settings:

```env
CHUNK_SIZE=1800
CHUNK_OVERLAP=150
```
