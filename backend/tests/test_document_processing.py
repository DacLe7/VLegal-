"""
Tests for Document Processing Pipeline
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_processor import DocumentProcessor
from app.services.metadata_extractor import MetadataExtractor, DocumentType
from app.services.legal_chunker import LegalChunker


class TestMetadataExtractor:
    """Tests for metadata extraction"""
    
    def setup_method(self):
        self.extractor = MetadataExtractor()
    
    def test_extract_luat_metadata(self):
        """Test extracting metadata from Luật filename"""
        metadata = self.extractor.extract_from_filename("Luật-13-2022-QH15.docx")
        
        assert metadata is not None
        assert metadata.document_number == "13/2022/QH15"
        assert metadata.document_type == DocumentType.LUAT
        assert metadata.year == 2022
        assert metadata.issuing_body == "QH15"
    
    def test_extract_bo_luat_metadata(self):
        """Test extracting metadata from Bộ luật filename"""
        metadata = self.extractor.extract_from_filename("Bộ-luật-91-2015-QH13.doc")
        
        assert metadata is not None
        assert metadata.document_number == "91/2015/QH13"
        assert metadata.document_type == DocumentType.BO_LUAT
        assert metadata.year == 2015
    
    def test_extract_title_from_content(self):
        """Test extracting title from document content"""
        content = """
        QUỐC HỘI
        --------
        LUẬT
        ĐẤT ĐAI
        
        Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;
        """
        
        title = self.extractor.extract_title_from_content(content)
        assert title is not None
        assert "ĐẤT ĐAI" in title


class TestLegalChunker:
    """Tests for legal document chunking"""
    
    def setup_method(self):
        self.chunker = LegalChunker()
    
    def test_find_articles(self):
        """Test finding articles in text"""
        text = """
        Điều 1. Phạm vi điều chỉnh
        Luật này quy định về quyền sở hữu.
        
        Điều 2. Đối tượng áp dụng
        Luật này áp dụng đối với mọi tổ chức, cá nhân.
        """
        
        articles = self.chunker._find_articles(text)
        
        assert len(articles) == 2
        assert articles[0]['number'] == '1'
        assert articles[1]['number'] == '2'
    
    def test_chunk_with_clauses(self):
        """Test chunking with clauses (Khoản)"""
        text = """
        Điều 1. Định nghĩa
        
        1. Quyền sở hữu là quyền của chủ sở hữu.
        
        2. Chủ sở hữu có quyền chiếm hữu.
        
        3. Chủ sở hữu có quyền sử dụng.
        """
        
        chunks = self.chunker.chunk_document(text)
        
        assert len(chunks) >= 1
        assert chunks[0].article_number == '1'
    
    def test_chunk_with_chapter(self):
        """Test finding chapter context"""
        text = """
        CHƯƠNG I
        NHỮNG QUY ĐỊNH CHUNG
        
        Điều 1. Phạm vi điều chỉnh
        Nội dung điều 1.
        """
        
        chunks = self.chunker.chunk_document(text)
        
        assert len(chunks) >= 1
        # First article should have chapter context
        for chunk in chunks:
            if chunk.article_number == '1':
                assert chunk.chapter == 'I'
                break
    
    def test_chunk_preserves_metadata(self):
        """Test that chunking preserves document metadata"""
        text = """
        Điều 1. Test
        Content here.
        """
        
        metadata = {"filename": "test.docx", "year": 2024}
        chunks = self.chunker.chunk_document(text, metadata)
        
        assert len(chunks) >= 1
        assert chunks[0].metadata.get('filename') == 'test.docx'


class TestDocumentProcessor:
    """Tests for document processor"""
    
    def test_supported_extensions(self):
        """Test that supported extensions are defined"""
        processor = DocumentProcessor()
        
        assert '.docx' in processor.SUPPORTED_EXTENSIONS
        assert '.doc' in processor.SUPPORTED_EXTENSIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
