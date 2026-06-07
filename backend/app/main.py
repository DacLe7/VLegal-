"""
FastAPI Main Application
V-Legal Bot - RAG Chatbot Pháp Luật
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import chat, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📁 Data directory: {settings.data_dir}")
    print(f"💾 Vector DB: {settings.chroma_persist_dir}")
    yield
    # Shutdown
    print(f"👋 Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    description="""
## V-Legal Bot - Trợ lý Pháp luật Việt Nam

Hệ thống chatbot thông minh chuyên về pháp luật Việt Nam, sử dụng công nghệ RAG (Retrieval-Augmented Generation).

### Tính năng chính:
- 💬 **Chat**: Hỏi đáp về pháp luật Việt Nam
- 🔍 **Tìm kiếm**: Tìm kiếm văn bản pháp luật liên quan
- 📚 **Trích dẫn**: Mọi câu trả lời đều kèm nguồn trích dẫn (Điều, Khoản, Văn bản)
- 📁 **Quản lý**: Upload và quản lý văn bản pháp luật

### Công nghệ:
- **RAG Framework**: LangChain
- **Vector Database**: ChromaDB
- **LLM**: Google Gemini 1.5 Pro
- **Embeddings**: multilingual-e5

### Lưu ý:
- Chatbot chỉ trả lời dựa trên dữ liệu pháp luật đã được nạp vào hệ thống
- Không thay thế tư vấn pháp lý chuyên nghiệp
    """,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/", tags=["Root"])
async def root():
    """API Root - Welcome message"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Trợ lý Pháp luật Việt Nam sử dụng RAG",
        "endpoints": {
            "chat": "/chat",
            "search": "/chat/search",
            "admin": "/admin",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
