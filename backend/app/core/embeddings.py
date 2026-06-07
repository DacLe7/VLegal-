"""
Embedding Service Module
Provides text embedding using multilingual models for Vietnamese legal text
"""
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """
    Embedding service for Vietnamese legal text
    Uses multilingual models optimized for semantic similarity
    """
    
    # Recommended models for Vietnamese
    RECOMMENDED_MODELS = {
        'multilingual-e5-large': 'intfloat/multilingual-e5-large',
        'multilingual-e5-base': 'intfloat/multilingual-e5-base',
        'paraphrase-multilingual': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
        'labse': 'sentence-transformers/LaBSE',
    }
    
    DEFAULT_MODEL = 'intfloat/multilingual-e5-base'  # Good balance of quality and speed
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding service
        
        Args:
            model_name: HuggingFace model name or key from RECOMMENDED_MODELS
        """
        if model_name is None:
            model_name = self.DEFAULT_MODEL
        elif model_name in self.RECOMMENDED_MODELS:
            model_name = self.RECOMMENDED_MODELS[model_name]
        
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model"""
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            print(f"Model loaded. Embedding dimension: {self._model.get_sentence_embedding_dimension()}")
        return self._model
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        return self.model.get_sentence_embedding_dimension()
    
    def _prepare_text(self, text: str, for_query: bool = False) -> str:
        """
        Prepare text for embedding
        E5 models require specific prefixes for best performance
        """
        if 'e5' in self.model_name.lower():
            if for_query:
                return f"query: {text}"
            else:
                return f"passage: {text}"
        return text
    
    def embed_text(self, text: str, for_query: bool = False) -> List[float]:
        """
        Embed a single text
        
        Args:
            text: Text to embed
            for_query: If True, prepare as query; if False, prepare as passage
        
        Returns:
            List of floats representing the embedding
        """
        prepared_text = self._prepare_text(text, for_query)
        embedding = self.model.encode(prepared_text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str], for_query: bool = False, batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple texts
        
        Args:
            texts: List of texts to embed
            for_query: If True, prepare as queries
            batch_size: Batch size for encoding
        
        Returns:
            List of embeddings
        """
        prepared_texts = [self._prepare_text(t, for_query) for t in texts]
        embeddings = self.model.encode(
            prepared_texts,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10
        )
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a search query"""
        return self.embed_text(query, for_query=True)
    
    def embed_documents(self, documents: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embed documents/passages"""
        return self.embed_texts(documents, for_query=False, batch_size=batch_size)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


# Singleton instance for reuse
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: Optional[str] = None) -> EmbeddingService:
    """Get or create the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None or (model_name and model_name != _embedding_service.model_name):
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service


if __name__ == "__main__":
    # Test the embedding service
    service = EmbeddingService()
    
    # Test with Vietnamese legal text
    texts = [
        "Quyền sở hữu bao gồm quyền chiếm hữu, quyền sử dụng và quyền định đoạt tài sản",
        "Người dân có quyền sở hữu nhà ở và đất đai theo quy định của pháp luật",
        "Thời tiết hôm nay rất đẹp",  # Unrelated text for comparison
    ]
    
    query = "Quyền sở hữu tài sản là gì?"
    
    # Embed
    doc_embeddings = service.embed_documents(texts)
    query_embedding = service.embed_query(query)
    
    print(f"Query: {query}\n")
    print("Similarities:")
    for text, doc_emb in zip(texts, doc_embeddings):
        sim = service.similarity(query_embedding, doc_emb)
        print(f"  {sim:.4f}: {text[:50]}...")
