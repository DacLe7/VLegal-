"""
RAG Engine Module
Core RAG pipeline: Retrieve → Augment → Generate
"""
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

from app.core.embeddings import EmbeddingService, get_embedding_service
from app.core.vector_store import VectorStore, SearchResult, get_vector_store
from app.core.llm import LLMService, get_llm_service
from app.core.prompts import (
    LEGAL_ASSISTANT_PROMPT,
    NO_CONTEXT_PROMPT,
    build_rag_prompt,
    format_context
)
from app.config import settings


@dataclass
class RAGResponse:
    """Response from the RAG pipeline"""
    answer: str
    sources: List[SearchResult]
    query: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'answer': self.answer,
            'query': self.query,
            'sources': [
                {
                    'content': s.content[:500] + "..." if len(s.content) > 500 else s.content,
                    'reference': s.reference,
                    'score': s.score,
                    'metadata': s.metadata
                }
                for s in self.sources
            ],
            'metadata': self.metadata
        }


class RAGEngine:
    """
    RAG Engine for Vietnamese Legal Q&A
    
    Pipeline:
    1. Embed the user query
    2. Retrieve relevant legal documents from vector store
    3. Build prompt with retrieved context
    4. Generate response using LLM
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        llm_service: Optional[LLMService] = None,
        top_k: int = None,
        min_relevance_score: float = 0.3
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        self.llm_service = llm_service or get_llm_service()
        self.top_k = top_k or settings.retrieval_top_k
        self.min_relevance_score = min_relevance_score
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User's question
            top_k: Number of results to retrieve
            filter_metadata: Optional metadata filters
        
        Returns:
            List of SearchResult objects
        """
        top_k = top_k or self.top_k
        
        # Embed the query
        query_embedding = self.embedding_service.embed_query(query)
        
        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Filter by minimum relevance score
        results = [r for r in results if r.score >= self.min_relevance_score]
        
        return results
    
    def generate(
        self,
        query: str,
        context_results: List[SearchResult],
        system_prompt: str = None
    ) -> str:
        """
        Generate response based on retrieved context
        
        Args:
            query: User's question
            context_results: Retrieved documents
            system_prompt: Optional custom system prompt
        
        Returns:
            Generated response text
        """
        if not context_results:
            return NO_CONTEXT_PROMPT
        
        # Build the RAG prompt
        prompt = build_rag_prompt(
            question=query,
            search_results=context_results,
            system_prompt=system_prompt
        )
        
        # Generate response
        response = self.llm_service.generate(prompt)
        
        return response
    
    def query(
        self,
        question: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> RAGResponse:
        """
        Complete RAG pipeline: Retrieve → Augment → Generate
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            filter_metadata: Optional filters (document_type, year, etc.)
            system_prompt: Optional custom system prompt
        
        Returns:
            RAGResponse with answer and sources
        """
        # Step 1: Retrieve
        sources = self.retrieve(
            query=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Step 2 & 3: Augment & Generate
        answer = self.generate(
            query=question,
            context_results=sources,
            system_prompt=system_prompt
        )
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            query=question,
            metadata={
                'top_k': top_k or self.top_k,
                'filter': filter_metadata,
                'sources_count': len(sources)
            }
        )
    
    def query_stream(
        self,
        question: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> Generator[str, None, None]:
        """
        Streaming version of query - yields response chunks
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            filter_metadata: Optional filters
            system_prompt: Optional custom system prompt
        
        Yields:
            Response text chunks
        """
        # Retrieve context
        sources = self.retrieve(
            query=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        if not sources:
            yield NO_CONTEXT_PROMPT
            return
        
        # Build prompt
        prompt = build_rag_prompt(
            question=question,
            search_results=sources,
            system_prompt=system_prompt
        )
        
        # Stream response
        for chunk in self.llm_service.generate_stream(prompt):
            yield chunk


# Singleton
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine singleton"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine


if __name__ == "__main__":
    # Test the RAG engine (requires API key and ingested data)
    import os
    
    if os.getenv("GEMINI_API_KEY"):
        engine = RAGEngine()
        
        # Test query
        response = engine.query("Quyền sở hữu tài sản được quy định như thế nào?")
        
        print("Question:", response.query)
        print("\nAnswer:", response.answer)
        print("\nSources:")
        for source in response.sources:
            print(f"  - {source.reference} (score: {source.score:.2%})")
    else:
        print("GEMINI_API_KEY not set. Skipping test.")
