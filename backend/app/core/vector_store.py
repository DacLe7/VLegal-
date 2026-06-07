"""
ChromaDB vector store for legal document chunks.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.legal_chunker import LegalChunk


@dataclass
class SearchResult:
    """A single vector search result."""

    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str

    @property
    def reference(self) -> str:
        parts = []

        if self.metadata.get("article_number"):
            parts.append(f"Điều {self.metadata['article_number']}")

        if self.metadata.get("clause_number"):
            parts.append(f"Khoản {self.metadata['clause_number']}")

        if self.metadata.get("point_number"):
            parts.append(f"Điểm {self.metadata['point_number']}")

        if self.metadata.get("document_number"):
            parts.append(f"({self.metadata['document_number']})")

        if self.metadata.get("filename"):
            parts.append(f"- {self.metadata['filename']}")

        return " ".join(parts) if parts else "Không rõ nguồn"


class VectorStore:
    """Vector store using ChromaDB for legal documents."""

    def __init__(
        self,
        persist_directory: str = "./vectordb",
        collection_name: str = "legal_documents",
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        return self._collection

    @staticmethod
    def _sanitize_id_part(value: Any, default: str = "") -> str:
        text = str(value or default).strip()

        if not text:
            return ""

        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.replace("đ", "d").replace("Đ", "D")
        text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")

        return text.upper()

    def _build_chunk_id(
        self,
        doc_meta: Dict[str, Any],
        chunk: LegalChunk,
        fallback_index: int,
        used_ids: Set[str],
    ) -> str:
        filename = Path(
            str(
                doc_meta.get("filename")
                or doc_meta.get("source")
                or "document"
            )
        ).stem

        parts = [self._sanitize_id_part(filename, "DOCUMENT")]

        if chunk.article_number:
            parts.append(f"D{self._sanitize_id_part(chunk.article_number)}")

        if chunk.clause_number:
            parts.append(f"K{self._sanitize_id_part(chunk.clause_number)}")

        if chunk.point_number:
            parts.append(f"P{self._sanitize_id_part(chunk.point_number)}")

        if len(parts) == 1:
            parts.append(self._sanitize_id_part(chunk.chunk_type, "CHUNK"))
            parts.append(str(fallback_index + 1))

        base_id = "_".join(part for part in parts if part)
        chunk_id = base_id
        suffix = 2

        while chunk_id in used_ids:
            chunk_id = f"{base_id}_{suffix}"
            suffix += 1

        used_ids.add(chunk_id)

        return chunk_id

    def add_chunks(
        self,
        chunks: List[LegalChunk],
        embeddings: List[List[float]],
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        if not chunks:
            return []

        ids = []
        documents = []
        metadatas = []

        doc_meta = document_metadata or {}
        used_ids: Set[str] = set()

        for i, chunk in enumerate(chunks):
            chunk_id = self._build_chunk_id(
                doc_meta=doc_meta,
                chunk=chunk,
                fallback_index=i,
                used_ids=used_ids,
            )

            ids.append(chunk_id)
            documents.append(chunk.content)

            metadata = {
                "chunk_type": chunk.chunk_type,
                "article_number": chunk.article_number or "",
                "clause_number": chunk.clause_number or "",
                "point_number": chunk.point_number or "",
                "chapter": chunk.chapter or "",
                "section": chunk.section or "",
                "reference": chunk.reference,
                **doc_meta,
            }

            metadatas.append(
                {
                    k: str(v) if v is not None else ""
                    for k, v in metadata.items()
                }
            )

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        where = (
            {
                k: str(v)
                for k, v in filter_metadata.items()
                if v
            }
            if filter_metadata
            else None
        )

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results: List[SearchResult] = []

        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]

                search_results.append(
                    SearchResult(
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i],
                        score=1 - distance,
                        chunk_id=chunk_id,
                    )
                )

        return search_results

    def delete_document(self, filename: str) -> int:
        results = self.collection.get(
            where={"filename": filename},
            include=[],
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])

        return 0

    def get_document_list(self) -> List[Dict[str, Any]]:
        results = self.collection.get(include=["metadatas"])

        documents: Dict[str, Dict[str, Any]] = {}

        for metadata in results["metadatas"]:
            filename = metadata.get("filename", "Unknown")

            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "document_number": metadata.get("document_number", ""),
                    "document_type": metadata.get("document_type", ""),
                    "year": metadata.get("year", ""),
                    "chunk_count": 0,
                }

            documents[filename]["chunk_count"] += 1

        return list(documents.values())

    def get_stats(self) -> Dict[str, Any]:
        documents = self.get_document_list()

        return {
            "total_chunks": self.collection.count(),
            "total_documents": len(documents),
            "collection_name": self.collection_name,
            "persist_directory": str(self.persist_directory),
        }

    def reset(self) -> None:
        self.client.delete_collection(self.collection_name)
        self._collection = None
        print(f"Collection '{self.collection_name}' has been reset")


_vector_store: Optional[VectorStore] = None


def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> VectorStore:
    """
    Get singleton VectorStore instance.

    Uses values from app.config.settings by default,
    so Render environment variables can control ChromaDB path
    and collection name.
    """
    global _vector_store

    persist_directory = persist_directory or settings.chroma_persist_dir
    collection_name = collection_name or settings.chroma_collection_name

    if _vector_store is None:
        _vector_store = VectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

    return _vector_store
