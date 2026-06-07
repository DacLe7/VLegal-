"""
FastAPI application entrypoint for the V-Legal RAG demo.

Startup must stay lightweight so Render can detect the bound port before
RAG dependencies are loaded.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, chat
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events without RAG initialization."""
    print("FastAPI app started")
    print("RAG services will be loaded lazily on request")
    yield
    print(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    description=(
        "V-Legal RAG Demo is a Retrieval-Augmented Generation demo for "
        "Vietnamese legal document lookup. RAG services are lazy-loaded "
        "only when request endpoints need them."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/", tags=["Root"])
async def root():
    """Lightweight root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "V-Legal RAG Demo",
        "rag_loading": "lazy",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "chat_health": "/chat/health",
            "search": "/chat/search",
            "admin": "/admin",
            "docs": "/docs",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Lightweight health check that does not load RAG services."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "rag_loading": "lazy",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
