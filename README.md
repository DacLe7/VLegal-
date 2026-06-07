# V-Legal RAG Demo

V-Legal RAG Demo is a Retrieval-Augmented Generation demo for VLegal AI LaborCare. This repository is RAG only, not GraphRAG, and it should remain deployable to GitHub and Render.

The demo retrieves relevant Vietnamese legal document chunks from ChromaDB, sends only the retrieved context to Gemini, and returns an answer with source references. It does not replace a lawyer, government agency, labor authority, social insurance agency, union, or court.

## Project Structure

```text
backend/      FastAPI API, ingestion, RAG pipeline
frontend/     Next.js demo UI
Data/         Legal DOCX dataset for ingestion
vectordb/     Local ChromaDB persistence, generated locally
```

The `Data/` folder can be replaced with another legal DOCX dataset. After changing the dataset, reingest the documents.

## Security

- Do not commit `.env`, `backend/.env`, `frontend/.env.local`, vector stores, build artifacts, or API keys.
- Do not put a real Gemini API key in `.env.example`, frontend env files, README, or source code.
- Before deployment, create `.env` locally or set environment variables in the Render dashboard.
- Treat any real API key that was committed or shared as leaked and rotate it.

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
python scripts/ingest_data.py --reset
python -m app.main
```

Recommended demo chunk settings:

```env
CHUNK_SIZE=1800
CHUNK_OVERLAP=150
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend default: `http://localhost:3000`

Backend default: `http://localhost:8000`

`frontend/.env.local.example` contains only:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Environment

Backend variables are documented in `.env.example` and `backend/.env.example`.

Important values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
CHROMA_PERSIST_DIR=./vectordb
CHROMA_COLLECTION_NAME=legal_documents
DATA_DIR=./Data
CHUNK_SIZE=1800
CHUNK_OVERLAP=150
LLM_MODEL=gemini-2.5-flash
RETRIEVAL_TOP_K=8
```

## Smoke Checks

From the repository root:

```bash
python -m py_compile backend/app/core/prompts.py backend/app/config.py backend/app/services/legal_chunker.py backend/app/core/vector_store.py
python -m py_compile backend/app/main.py backend/app/api/routes/chat.py backend/app/api/routes/admin.py
python backend/scripts/smoke_test_config.py
python backend/scripts/smoke_test_startup.py
```

The smoke test checks that `GEMINI_API_KEY` is set without printing it, the data folder exists, chunk settings are valid, frontend env example is public-only, and local env files are ignored.

## Render

See `DEPLOY_RENDER.md`.

For Render, the backend start command remains:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The backend binds its port before loading RAG services. ChromaDB, embeddings, Gemini, and the RAG engine are lazy-loaded on the first API request that needs them.

Frontend Render env:

```env
NEXT_PUBLIC_API_URL=https://vlegal-rag-backend.onrender.com
```

Backend Render env can include:

```env
FRONTEND_ORIGINS=https://vlegal-rag-frontend.onrender.com,http://localhost:3000,http://127.0.0.1:3000
```
