"""
Admin API Routes
Endpoints for document management and system administration
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
import shutil

from app.core.vector_store import get_vector_store
from app.core.embeddings import get_embedding_service
from app.services.document_processor import DocumentProcessor
from app.services.metadata_extractor import MetadataExtractor, DocumentStatus
from app.services.legal_chunker import LegalChunker
from app.config import settings


router = APIRouter(prefix="/admin", tags=["Admin"])


class DocumentInfo(BaseModel):
    """Information about a document in the system"""
    filename: str
    document_number: str
    document_type: str
    year: str
    chunk_count: int
    status: str = "Còn hiệu lực"


class DocumentListResponse(BaseModel):
    """Response for document list"""
    total_documents: int
    total_chunks: int
    documents: List[DocumentInfo]


class UploadResponse(BaseModel):
    """Response for document upload"""
    filename: str
    status: str
    chunks_created: int
    message: str


class SystemStats(BaseModel):
    """System statistics"""
    total_documents: int
    total_chunks: int
    collection_name: str
    vector_db_path: str


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """
    Liệt kê tất cả văn bản đã được nạp vào hệ thống
    """
    try:
        vector_store = get_vector_store()
        documents = vector_store.get_document_list()
        stats = vector_store.get_stats()
        
        return DocumentListResponse(
            total_documents=stats['total_documents'],
            total_chunks=stats['total_chunks'],
            documents=[
                DocumentInfo(
                    filename=doc['filename'],
                    document_number=doc.get('document_number', ''),
                    document_type=doc.get('document_type', ''),
                    year=doc.get('year', ''),
                    chunk_count=doc['chunk_count']
                )
                for doc in documents
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy danh sách: {str(e)}")


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """
    Lấy thống kê hệ thống
    """
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return SystemStats(
            total_documents=stats['total_documents'],
            total_chunks=stats['total_chunks'],
            collection_name=stats['collection_name'],
            vector_db_path=stats['persist_directory']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy thống kê: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="File văn bản pháp luật (.docx hoặc .doc)"),
    status: str = Form(default="Còn hiệu lực", description="Trạng thái hiệu lực")
):
    """
    Upload văn bản pháp luật mới
    
    - **file**: File Word (.docx hoặc .doc)
    - **status**: Trạng thái hiệu lực (Còn hiệu lực / Hết hiệu lực)
    """
    # Validate file type
    if not file.filename.endswith(('.docx', '.doc')):
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ file .docx hoặc .doc"
        )
    
    try:
        # Save file to Data directory
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / file.filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Process document
        result = await _process_and_ingest(file_path, status)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload: {str(e)}")


async def _process_and_ingest(file_path: Path, status: str) -> UploadResponse:
    """Process and ingest a document"""
    try:
        # Initialize services
        doc_processor = DocumentProcessor()
        metadata_extractor = MetadataExtractor()
        chunker = LegalChunker()
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        
        # Process document
        doc = doc_processor.process_document(file_path)
        if not doc:
            return UploadResponse(
                filename=file_path.name,
                status="error",
                chunks_created=0,
                message="Không thể đọc file"
            )
        
        # Extract metadata
        metadata = metadata_extractor.extract_metadata(file_path.name, doc.content)
        doc_metadata = {
            'filename': file_path.name,
            'filepath': str(file_path),
            'status': status,
            **metadata.to_dict()
        }
        
        # Chunk document
        chunks = chunker.chunk_document(doc.content, doc_metadata)
        
        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embedding_service.embed_documents(chunk_texts)
        
        # Store in vector database
        chunk_ids = vector_store.add_chunks(chunks, embeddings, doc_metadata)
        
        return UploadResponse(
            filename=file_path.name,
            status="success",
            chunks_created=len(chunk_ids),
            message=f"Đã nạp thành công {len(chunk_ids)} đoạn văn bản"
        )
    
    except Exception as e:
        return UploadResponse(
            filename=file_path.name,
            status="error",
            chunks_created=0,
            message=str(e)
        )


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Xóa văn bản khỏi hệ thống
    
    - **filename**: Tên file cần xóa
    """
    try:
        vector_store = get_vector_store()
        deleted_count = vector_store.delete_document(filename)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy văn bản: {filename}"
            )
        
        return {
            "message": f"Đã xóa {deleted_count} chunks của {filename}",
            "filename": filename,
            "chunks_deleted": deleted_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa văn bản: {str(e)}")


@router.post("/documents/{filename}/status")
async def update_document_status(
    filename: str,
    status: str = Form(..., description="Trạng thái mới (Còn hiệu lực / Hết hiệu lực)")
):
    """
    Cập nhật trạng thái hiệu lực của văn bản
    
    Khi văn bản hết hiệu lực, nó sẽ bị đánh dấu và ít được ưu tiên trong kết quả tìm kiếm.
    """
    # Note: ChromaDB doesn't support updating metadata directly
    # This would require delete and re-add, which is expensive
    # For now, we'll just return a message
    return {
        "message": f"Chức năng cập nhật trạng thái sẽ được hỗ trợ trong phiên bản tiếp theo",
        "filename": filename,
        "requested_status": status
    }


@router.post("/reset")
async def reset_vector_store():
    """
    Reset toàn bộ vector store (XÓA TẤT CẢ DỮ LIỆU)
    
    ⚠️ Cảnh báo: Thao tác này không thể hoàn tác!
    """
    try:
        vector_store = get_vector_store()
        vector_store.reset()
        
        return {
            "message": "Đã reset vector store thành công",
            "warning": "Tất cả dữ liệu đã bị xóa. Cần chạy lại script ingest để nạp dữ liệu."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi reset: {str(e)}")
