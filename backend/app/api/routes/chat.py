"""
Chat API routes.

RAG dependencies are imported lazily inside request handlers so /health and app
startup stay lightweight on Render Free.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question", min_length=1)
    top_k: int = Field(default=5, description="Number of retrieved sources", ge=1, le=20)
    document_type: Optional[str] = Field(default=None, description="Filter by document type")
    year: Optional[int] = Field(default=None, description="Filter by year")
    stream: bool = Field(default=False, description="Streaming response")


class ChatResponse(BaseModel):
    answer: str
    query: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceInfo(BaseModel):
    content: str
    reference: str
    score: float
    filename: str
    document_type: str
    document_number: str


def _load_rag_engine():
    try:
        from app.core.rag_engine import get_rag_engine

        return get_rag_engine()
    except Exception as exc:
        logger.exception("RAG service failed to initialize")
        raise HTTPException(
            status_code=500,
            detail="RAG service failed to initialize. Check backend logs.",
        ) from exc


def _filter_metadata(document_type: Optional[str] = None, year: Optional[int] = None) -> Optional[Dict[str, str]]:
    filters: Dict[str, str] = {}
    if document_type:
        filters["document_type"] = document_type
    if year:
        filters["year"] = str(year)
    return filters or None


def _source_to_dict(source) -> Dict[str, Any]:
    return {
        "content": source.content[:500] + "..." if len(source.content) > 500 else source.content,
        "reference": source.reference,
        "score": source.score,
        "filename": source.metadata.get("filename", ""),
        "document_type": source.metadata.get("document_type", ""),
        "document_number": source.metadata.get("document_number", ""),
    }


@router.post("", response_model=ChatResponse, include_in_schema=False)
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        engine = _load_rag_engine()
        filters = _filter_metadata(request.document_type, request.year)

        if request.stream:
            return StreamingResponse(
                _stream_response(engine, request.question, request.top_k, filters),
                media_type="text/event-stream",
            )

        response = engine.query(
            question=request.question,
            top_k=request.top_k,
            filter_metadata=filters,
        )

        return ChatResponse(
            answer=response.answer,
            query=response.query,
            sources=[_source_to_dict(source) for source in response.sources],
            metadata=response.metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=500,
            detail="Chat request failed. Check backend logs.",
        ) from exc


async def _stream_response(engine, question: str, top_k: int, filter_metadata: Optional[Dict[str, str]]):
    try:
        for chunk in engine.query_stream(
            question=question,
            top_k=top_k,
            filter_metadata=filter_metadata,
        ):
            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception:
        logger.exception("Streaming chat request failed")
        yield f"data: {json.dumps({'error': 'Chat stream failed. Check backend logs.'})}\n\n"


@router.post("/search", response_model=List[SourceInfo])
async def search_documents(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(default=10, ge=1, le=50, description="Maximum result count"),
    document_type: Optional[str] = Query(default=None, description="Filter by document type"),
):
    try:
        engine = _load_rag_engine()
        results = engine.retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=_filter_metadata(document_type=document_type),
        )

        return [
            SourceInfo(
                content=result.content,
                reference=result.reference,
                score=result.score,
                filename=result.metadata.get("filename", ""),
                document_type=result.metadata.get("document_type", ""),
                document_number=result.metadata.get("document_number", ""),
            )
            for result in results
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Search request failed")
        raise HTTPException(
            status_code=500,
            detail="Search request failed. Check backend logs.",
        ) from exc


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chat", "rag_loading": "lazy"}
