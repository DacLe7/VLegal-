"""
Chat API Routes
Endpoints for chatbot interactions
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from app.core.rag_engine import get_rag_engine, RAGResponse


router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    question: str = Field(..., description="Câu hỏi của người dùng", min_length=1)
    top_k: int = Field(default=5, description="Số lượng tài liệu tham khảo", ge=1, le=20)
    document_type: Optional[str] = Field(default=None, description="Lọc theo loại văn bản (Luật, Nghị định, Thông tư)")
    year: Optional[int] = Field(default=None, description="Lọc theo năm ban hành")
    stream: bool = Field(default=False, description="Streaming response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    answer: str = Field(..., description="Câu trả lời từ chatbot")
    query: str = Field(..., description="Câu hỏi gốc")
    sources: List[Dict[str, Any]] = Field(default=[], description="Nguồn tham khảo")
    metadata: Dict[str, Any] = Field(default={}, description="Metadata")


class SourceInfo(BaseModel):
    """Information about a source document"""
    content: str
    reference: str
    score: float
    filename: str
    document_type: str
    document_number: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Đặt câu hỏi pháp luật cho chatbot
    
    - **question**: Câu hỏi của bạn về pháp luật Việt Nam
    - **top_k**: Số lượng tài liệu tham khảo (mặc định: 5)
    - **document_type**: Lọc theo loại văn bản (Luật, Nghị định, Thông tư)
    - **year**: Lọc theo năm ban hành
    - **stream**: Sử dụng streaming response
    """
    try:
        engine = get_rag_engine()
        
        # Build filter metadata
        filter_metadata = {}
        if request.document_type:
            filter_metadata['document_type'] = request.document_type
        if request.year:
            filter_metadata['year'] = str(request.year)
        
        # Handle streaming
        if request.stream:
            return StreamingResponse(
                _stream_response(engine, request.question, request.top_k, filter_metadata or None),
                media_type="text/event-stream"
            )
        
        # Regular response
        response = engine.query(
            question=request.question,
            top_k=request.top_k,
            filter_metadata=filter_metadata or None
        )
        
        return ChatResponse(
            answer=response.answer,
            query=response.query,
            sources=[
                {
                    'content': s.content[:500] + "..." if len(s.content) > 500 else s.content,
                    'reference': s.reference,
                    'score': s.score,
                    'filename': s.metadata.get('filename', ''),
                    'document_type': s.metadata.get('document_type', ''),
                    'document_number': s.metadata.get('document_number', '')
                }
                for s in response.sources
            ],
            metadata=response.metadata
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý câu hỏi: {str(e)}")


async def _stream_response(engine, question: str, top_k: int, filter_metadata: Optional[Dict]):
    """Generator for streaming response"""
    try:
        for chunk in engine.query_stream(
            question=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        ):
            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/search", response_model=List[SourceInfo])
async def search_documents(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    top_k: int = Query(default=10, ge=1, le=50, description="Số kết quả tối đa"),
    document_type: Optional[str] = Query(default=None, description="Lọc theo loại văn bản")
):
    """
    Tìm kiếm văn bản pháp luật liên quan
    
    Trả về danh sách các đoạn văn bản có độ liên quan cao nhất với từ khóa tìm kiếm.
    """
    try:
        engine = get_rag_engine()
        
        filter_metadata = {}
        if document_type:
            filter_metadata['document_type'] = document_type
        
        results = engine.retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata or None
        )
        
        return [
            SourceInfo(
                content=r.content,
                reference=r.reference,
                score=r.score,
                filename=r.metadata.get('filename', ''),
                document_type=r.metadata.get('document_type', ''),
                document_number=r.metadata.get('document_number', '')
            )
            for r in results
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm: {str(e)}")


@router.get("/health")
async def health_check():
    """Kiểm tra trạng thái service"""
    return {"status": "healthy", "service": "chat"}
