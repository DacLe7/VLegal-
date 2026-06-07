"""
Embedding service for Vietnamese legal text.

The model is loaded lazily so app startup and /health stay lightweight.
"""

import os
from typing import List, Optional

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from sentence_transformers import SentenceTransformer
import numpy as np

from app.config import settings

try:
    import torch

    torch.set_num_threads(1)
except Exception as exc:
    print(f"Torch thread limit not applied: {exc}")


class EmbeddingService:
    """Embedding service for Vietnamese legal text."""

    RECOMMENDED_MODELS = {
        "multilingual-e5-small": "intfloat/multilingual-e5-small",
        "multilingual-e5-base": "intfloat/multilingual-e5-base",
        "multilingual-e5-large": "intfloat/multilingual-e5-large",
        "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "labse": "sentence-transformers/LaBSE",
    }

    DEFAULT_MODEL = "intfloat/multilingual-e5-small"

    def __init__(self, model_name: Optional[str] = None):
        if model_name is None:
            model_name = settings.embedding_model or self.DEFAULT_MODEL
        elif model_name in self.RECOMMENDED_MODELS:
            model_name = self.RECOMMENDED_MODELS[model_name]

        self.model_name = model_name
        self._model = None
        print(f"Embedding service configured with model: {self.model_name}")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name, device="cpu")
            print(
                "Embedding model loaded. "
                f"Dimension: {self._model.get_sentence_embedding_dimension()}"
            )
        return self._model

    @property
    def embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def _prepare_text(self, text: str, for_query: bool = False) -> str:
        if "e5" in self.model_name.lower():
            return f"query: {text}" if for_query else f"passage: {text}"
        return text

    def embed_text(self, text: str, for_query: bool = False) -> List[float]:
        prepared_text = self._prepare_text(text, for_query)
        embedding = self.model.encode(
            prepared_text,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def embed_texts(
        self,
        texts: List[str],
        for_query: bool = False,
        batch_size: int = 16,
    ) -> List[List[float]]:
        prepared_texts = [self._prepare_text(t, for_query) for t in texts]
        embeddings = self.model.encode(
            prepared_texts,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        return self.embed_text(query, for_query=True)

    def embed_documents(self, documents: List[str], batch_size: int = 16) -> List[List[float]]:
        return self.embed_texts(documents, for_query=False, batch_size=batch_size)

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: Optional[str] = None) -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None or (model_name and model_name != _embedding_service.model_name):
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
