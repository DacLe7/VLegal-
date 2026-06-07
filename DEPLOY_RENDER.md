# Deploying to Render

This repository is a RAG demo for VLegal AI LaborCare. It is not a GraphRAG implementation.

## Backend service

- Runtime: Python
- Python version: `3.11.10` via `.python-version`
- Build command: `cd backend && pip install -r requirements.txt && python scripts/ingest_data.py`
- Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set environment variables in the Render dashboard.
- `GEMINI_API_KEY` must be set in Render, not committed to this repository.
- `FRONTEND_ORIGINS` can be set to `https://vlegal-rag-frontend.onrender.com,http://localhost:3000,http://127.0.0.1:3000`.
- Use `CHROMA_PERSIST_DIR`, `DATA_DIR`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `RETRIEVAL_TOP_K` from `.env.example` as deployment defaults.
- The backend must bind its port quickly before loading RAG services.
- RAG services are lazy-loaded on the first API request that needs retrieval or generation.

## Frontend service

- Runtime: Node
- Build command: `cd frontend && npm install && npm run build`
- Start command: `cd frontend && npm start`
- Set `NEXT_PUBLIC_API_URL=/api/backend`.
- Set `BACKEND_API_URL=https://vlegal-rag-backend.onrender.com`.
- Browser chat requests go to same-origin `POST /api/backend/chat`; Next.js forwards that exact path to backend `POST /chat/`.

## ChromaDB storage

ChromaDB local storage may need a persistent disk on Render. For a small demo dataset, reingesting during deployment is acceptable, but production-like demos should use persistent storage or a managed vector database.
