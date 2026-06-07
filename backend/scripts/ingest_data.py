"""
Data Ingestion Script
Processes all legal documents and ingests them into the vector store
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env from backend directory BEFORE importing app modules
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"Loaded .env from: {env_file}")
else:
    print(f"WARNING: .env not found at {env_file}")

# Now import after env is loaded
from typing import List, Dict, Any
from tqdm import tqdm

from app.services.document_processor import DocumentProcessor, ProcessedDocument
from app.services.metadata_extractor import MetadataExtractor
from app.services.legal_chunker import LegalChunker, LegalChunk
from app.core.embeddings import EmbeddingService
from app.core.vector_store import VectorStore

# Get settings from environment
DATA_DIR = os.getenv("DATA_DIR", str(project_root.parent / "Data"))
VECTORDB_DIR = os.getenv("CHROMA_PERSIST_DIR", str(project_root.parent / "vectordb"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "legal_documents")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))


class DataIngestionPipeline:
    """Pipeline for ingesting legal documents into the vector store"""
    
    def __init__(
        self,
        data_dir: str = None,
        vectordb_dir: str = None,
        collection_name: str = None
    ):
        self.data_dir = data_dir or DATA_DIR
        self.vectordb_dir = vectordb_dir or VECTORDB_DIR
        self.collection_name = collection_name or COLLECTION_NAME
        
        # Initialize components
        self.doc_processor = DocumentProcessor(self.data_dir)
        self.metadata_extractor = MetadataExtractor()
        self.chunker = LegalChunker(
            chunk_by_article=True,
            max_chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(self.vectordb_dir, self.collection_name)
    
    def process_single_document(
        self,
        filepath: Path,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Process and ingest a single document
        
        Returns:
            Dict with processing statistics
        """
        filename = filepath.name
        
        # Check if already exists
        if skip_existing:
            existing = self.vector_store.collection.get(
                where={"filename": filename},
                limit=1
            )
            if existing['ids']:
                return {
                    'filename': filename,
                    'status': 'skipped',
                    'reason': 'already exists',
                    'chunks': 0
                }
        
        # Process document
        doc = self.doc_processor.process_document(filepath)
        if not doc:
            return {
                'filename': filename,
                'status': 'error',
                'reason': 'failed to read document',
                'chunks': 0
            }
        
        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(filename, doc.content)
        doc_metadata = {
            'filename': filename,
            'filepath': str(filepath),
            **metadata.to_dict()
        }
        
        # Chunk document
        chunks = self.chunker.chunk_document(doc.content, doc_metadata)
        if not chunks:
            return {
                'filename': filename,
                'status': 'error',
                'reason': 'no chunks created',
                'chunks': 0
            }
        
        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(chunk_texts)
        
        # Store in vector database
        chunk_ids = self.vector_store.add_chunks(chunks, embeddings, doc_metadata)
        
        return {
            'filename': filename,
            'status': 'success',
            'chunks': len(chunk_ids),
            'metadata': doc_metadata
        }
    
    def ingest_all(
        self,
        skip_existing: bool = True,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest all documents from the data directory
        
        Returns:
            Dict with overall statistics
        """
        documents = self.doc_processor.list_documents()
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"V-Legal Bot - Data Ingestion Pipeline")
            print(f"{'='*60}")
            print(f"Data directory: {self.data_dir}")
            print(f"Vector DB: {self.vectordb_dir}")
            print(f"Documents found: {len(documents)}")
            print(f"{'='*60}\n")
        
        results = {
            'total': len(documents),
            'success': 0,
            'skipped': 0,
            'errors': 0,
            'total_chunks': 0,
            'documents': []
        }
        
        iterator = tqdm(documents, desc="Processing") if verbose else documents
        
        for filepath in iterator:
            result = self.process_single_document(filepath, skip_existing)
            results['documents'].append(result)
            
            if result['status'] == 'success':
                results['success'] += 1
                results['total_chunks'] += result['chunks']
            elif result['status'] == 'skipped':
                results['skipped'] += 1
            else:
                results['errors'] += 1
        
        if verbose:
            print(f"\n{'='*60}")
            print("Ingestion Complete!")
            print(f"{'='*60}")
            print(f"  Success: {results['success']}")
            print(f"  Skipped: {results['skipped']}")
            print(f"  Errors: {results['errors']}")
            print(f"  Total chunks created: {results['total_chunks']}")
            print(f"{'='*60}\n")
        
        return results
    
    def reset_and_reingest(self, verbose: bool = True) -> Dict[str, Any]:
        """Reset the vector store and reingest all documents"""
        if verbose:
            print("Resetting vector store...")
        self.vector_store.reset()
        return self.ingest_all(skip_existing=False, verbose=verbose)


def main():
    """Main entry point for data ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest legal documents into vector store")
    parser.add_argument("--data-dir", default=None, help="Directory containing legal documents")
    parser.add_argument("--vectordb-dir", default=None, help="Directory for vector database")
    parser.add_argument("--collection", default=None, help="Collection name")
    parser.add_argument("--reset", action="store_true", help="Reset and reingest all documents")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    # Use args if provided, otherwise use env variables
    pipeline = DataIngestionPipeline(
        data_dir=args.data_dir or DATA_DIR,
        vectordb_dir=args.vectordb_dir or VECTORDB_DIR,
        collection_name=args.collection or COLLECTION_NAME
    )
    
    if args.reset:
        results = pipeline.reset_and_reingest(verbose=not args.quiet)
    else:
        results = pipeline.ingest_all(verbose=not args.quiet)
    
    return results


if __name__ == "__main__":
    main()
