"""
Metadata Extractor Module
Extracts legal document metadata from filename and content
"""
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Types of legal documents"""
    LUAT = "Luật"
    BO_LUAT = "Bộ luật"
    NGHI_DINH = "Nghị định"
    THONG_TU = "Thông tư"
    QUYET_DINH = "Quyết định"
    UNKNOWN = "Không xác định"


class DocumentStatus(str, Enum):
    """Document validity status"""
    HIEU_LUC = "Còn hiệu lực"
    HET_HIEU_LUC = "Hết hiệu lực"
    CHUA_CO_HIEU_LUC = "Chưa có hiệu lực"


@dataclass
class LegalMetadata:
    """Metadata for a legal document"""
    document_number: str  # Số hiệu: 91/2015/QH13
    document_type: DocumentType
    issuing_body: str  # Cơ quan ban hành: QH13
    year: int
    effective_date: Optional[str] = None
    status: DocumentStatus = DocumentStatus.HIEU_LUC
    title: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_number": self.document_number,
            "document_type": self.document_type.value,
            "issuing_body": self.issuing_body,
            "year": self.year,
            "effective_date": self.effective_date,
            "status": self.status.value,
            "title": self.title
        }


class MetadataExtractor:
    """Extracts metadata from legal documents"""
    
    # Patterns for Vietnamese legal document filenames
    # Examples: Luật-13-2022-QH15.docx, Bộ-luật-91-2015-QH13.doc
    FILENAME_PATTERNS = [
        # Bộ luật pattern: Bộ-luật-91-2015-QH13
        r"Bộ-luật-(\d+)-(\d{4})-([A-Z]+\d+)",
        # Luật pattern: Luật-13-2022-QH15
        r"Luật-(\d+)-(\d{4})-([A-Z]+\d+)",
        # Nghị định pattern
        r"Nghị-định-(\d+)-(\d{4})-([A-Z]+)",
        # Generic pattern: Number-Year-IssuingBody
        r"(\d+)-(\d{4})-([A-Z]+\d*)",
    ]
    
    # Pattern to extract title from content
    TITLE_PATTERNS = [
        r"LUẬT\s+(.+?)(?:\n|Căn cứ)",
        r"BỘ LUẬT\s+(.+?)(?:\n|Căn cứ)",
        r"NGHỊ ĐỊNH\s+(.+?)(?:\n|Căn cứ)",
    ]
    
    def extract_from_filename(self, filename: str) -> Optional[LegalMetadata]:
        """Extract metadata from filename"""
        # Remove extension
        name = filename.rsplit('.', 1)[0]
        
        # Determine document type
        doc_type = DocumentType.UNKNOWN
        if name.startswith("Bộ-luật"):
            doc_type = DocumentType.BO_LUAT
        elif name.startswith("Luật"):
            doc_type = DocumentType.LUAT
        elif name.startswith("Nghị-định"):
            doc_type = DocumentType.NGHI_DINH
        elif name.startswith("Thông-tư"):
            doc_type = DocumentType.THONG_TU
        
        # Try each pattern
        for pattern in self.FILENAME_PATTERNS:
            match = re.search(pattern, name)
            if match:
                number, year, issuing_body = match.groups()
                doc_number = f"{number}/{year}/{issuing_body}"
                
                return LegalMetadata(
                    document_number=doc_number,
                    document_type=doc_type,
                    issuing_body=issuing_body,
                    year=int(year)
                )
        
        return None
    
    def extract_title_from_content(self, content: str) -> Optional[str]:
        """Extract document title from content"""
        # Get first 2000 chars for title search
        header = content[:2000]
        
        for pattern in self.TITLE_PATTERNS:
            match = re.search(pattern, header, re.DOTALL | re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up title
                title = re.sub(r'\s+', ' ', title)
                return title[:200]  # Limit length
        
        return None
    
    def extract_effective_date(self, content: str) -> Optional[str]:
        """Extract effective date from content"""
        # Pattern: "có hiệu lực từ ngày DD/MM/YYYY" or similar
        patterns = [
            r"có hiệu lực (?:thi hành )?(?:từ|kể từ) ngày (\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
            r"hiệu lực từ ngày (\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_metadata(self, filename: str, content: str = "") -> LegalMetadata:
        """Extract all metadata from filename and content"""
        # Start with filename metadata
        metadata = self.extract_from_filename(filename)
        
        if metadata is None:
            # Create default metadata
            metadata = LegalMetadata(
                document_number="Unknown",
                document_type=DocumentType.UNKNOWN,
                issuing_body="Unknown",
                year=0
            )
        
        # Enhance with content if available
        if content:
            # Extract title
            title = self.extract_title_from_content(content)
            if title:
                metadata.title = title
            
            # Extract effective date
            effective_date = self.extract_effective_date(content)
            if effective_date:
                metadata.effective_date = effective_date
        
        return metadata


if __name__ == "__main__":
    # Test the extractor
    extractor = MetadataExtractor()
    
    test_files = [
        "Luật-13-2022-QH15.docx",
        "Bộ-luật-91-2015-QH13.doc",
        "Luật-42-2024-QH15.docx",
    ]
    
    for filename in test_files:
        metadata = extractor.extract_from_filename(filename)
        if metadata:
            print(f"\n{filename}:")
            print(f"  Number: {metadata.document_number}")
            print(f"  Type: {metadata.document_type.value}")
            print(f"  Year: {metadata.year}")
            print(f"  Issuing Body: {metadata.issuing_body}")
