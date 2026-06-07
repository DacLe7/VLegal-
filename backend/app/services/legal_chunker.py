"""
Legal chunker for Vietnamese legal documents.

The chunking strategy keeps legal citation units intact where possible:
article -> clause -> point -> paragraph fallback.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LegalChunk:
    """A chunk of legal text with legal citation context."""

    content: str
    chunk_type: str
    article_number: Optional[str] = None
    clause_number: Optional[str] = None
    point_number: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def reference(self) -> str:
        parts = []
        if self.article_number:
            parts.append(f"Điều {self.article_number}")
        if self.clause_number:
            parts.append(f"Khoản {self.clause_number}")
        if self.point_number:
            parts.append(f"Điểm {self.point_number}")
        if self.chapter:
            parts.append(f"Chương {self.chapter}")
        return ", ".join(parts) if parts else "Phần mở đầu"


class LegalChunker:
    """Split legal documents by Vietnamese legal structure."""

    PATTERNS = {
        "part": r"^PHẦN\s+(THỨ\s+)?([IVXLCDM]+|\d+)[.:\s]*(.*?)$",
        "chapter": r"^CHƯƠNG\s+([IVXLCDM]+|\d+)[.:\s]*(.*?)$",
        "section": r"^MỤC\s+(\d+)[.:\s]*(.*?)$",
        "article": r"^Điều\s+(\d+[a-zA-Z]?)\s*[.:\-]?\s*(.*?)$",
        "clause": r"^(\d+[a-zA-Z]?)\.\s+",
        "point": r"^([a-zđ])\)\s+",
    }

    def __init__(
        self,
        chunk_by_article: bool = True,
        include_context: bool = True,
        max_chunk_size: int = 1800,
        min_chunk_size: int = 100,
        chunk_overlap: int = 150,
    ):
        self.chunk_by_article = chunk_by_article
        self.include_context = include_context
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.chunk_overlap = max(0, chunk_overlap)
        self.compiled_patterns = {
            name: re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    def _find_articles(self, text: str) -> List[Dict[str, Any]]:
        articles = []
        for match in self.compiled_patterns["article"].finditer(text):
            articles.append(
                {
                    "number": match.group(1),
                    "title": match.group(2).strip() if match.group(2) else "",
                    "start": match.start(),
                    "header_end": match.end(),
                }
            )

        for i, article in enumerate(articles):
            article["end"] = articles[i + 1]["start"] if i + 1 < len(articles) else len(text)
        return articles

    def _find_context_for_position(self, text: str, position: int, pattern_name: str) -> Optional[str]:
        current = None
        for match in self.compiled_patterns[pattern_name].finditer(text):
            if match.start() > position:
                break
            current = match.group(1)
        return current

    def _split_by_pattern(self, text: str, pattern_name: str) -> List[Dict[str, Any]]:
        matches = list(self.compiled_patterns[pattern_name].finditer(text))
        blocks = []
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            blocks.append(
                {
                    "number": match.group(1),
                    "start": match.start(),
                    "end": end,
                    "text": text[match.start():end].strip(),
                }
            )
        return blocks

    def _chunk_with_metadata(
        self,
        content: str,
        chunk_type: str,
        metadata: Dict[str, Any],
        article_number: Optional[str] = None,
        clause_number: Optional[str] = None,
        point_number: Optional[str] = None,
        chapter: Optional[str] = None,
        section: Optional[str] = None,
    ) -> LegalChunk:
        return LegalChunk(
            content=content.strip(),
            chunk_type=chunk_type,
            article_number=article_number,
            clause_number=clause_number,
            point_number=point_number,
            chapter=chapter,
            section=section,
            metadata=metadata,
        )

    def _split_clause_into_points(
        self,
        clause_text: str,
        article_number: str,
        clause_number: Optional[str],
        metadata: Dict[str, Any],
        chapter: Optional[str],
        section: Optional[str],
    ) -> List[LegalChunk]:
        point_blocks = self._split_by_pattern(clause_text, "point")
        if not point_blocks:
            return self._fallback_chunking(
                clause_text,
                metadata,
                chunk_type="clause_part",
                article_number=article_number,
                clause_number=clause_number,
                chapter=chapter,
                section=section,
            )

        chunks = []
        intro = clause_text[: point_blocks[0]["start"]].strip()
        for point in point_blocks:
            point_text = point["text"]
            if intro:
                point_text = f"{intro}\n\n{point_text}"
            if len(point_text) <= self.max_chunk_size:
                chunks.append(
                    self._chunk_with_metadata(
                        point_text,
                        "point",
                        metadata,
                        article_number=article_number,
                        clause_number=clause_number,
                        point_number=point["number"],
                        chapter=chapter,
                        section=section,
                    )
                )
            else:
                chunks.extend(
                    self._fallback_chunking(
                        point_text,
                        metadata,
                        chunk_type="point_part",
                        article_number=article_number,
                        clause_number=clause_number,
                        point_number=point["number"],
                        chapter=chapter,
                        section=section,
                    )
                )
            intro = ""
        return chunks

    def _split_article_into_clauses(
        self,
        article_text: str,
        article_number: str,
        metadata: Dict[str, Any],
        chapter: Optional[str],
        section: Optional[str],
    ) -> List[LegalChunk]:
        clause_blocks = self._split_by_pattern(article_text, "clause")
        if not clause_blocks:
            return self._fallback_chunking(
                article_text,
                metadata,
                chunk_type="article_part",
                article_number=article_number,
                chapter=chapter,
                section=section,
            )

        chunks = []
        intro = article_text[: clause_blocks[0]["start"]].strip()
        for clause in clause_blocks:
            clause_text = clause["text"]
            if intro:
                clause_text = f"{intro}\n\n{clause_text}"

            has_points = bool(self.compiled_patterns["point"].search(clause_text))
            if len(clause_text) <= self.max_chunk_size and not has_points:
                chunks.append(
                    self._chunk_with_metadata(
                        clause_text,
                        "clause",
                        metadata,
                        article_number=article_number,
                        clause_number=clause["number"],
                        chapter=chapter,
                        section=section,
                    )
                )
            else:
                chunks.extend(
                    self._split_clause_into_points(
                        clause_text,
                        article_number,
                        clause["number"],
                        metadata,
                        chapter,
                        section,
                    )
                )
            intro = ""
        return chunks

    def chunk_document(self, text: str, metadata: Dict[str, Any] = None) -> List[LegalChunk]:
        """Chunk a legal document into citation-preserving pieces."""
        metadata = metadata or {}
        text = text.strip()
        if not text:
            return []

        articles = self._find_articles(text)
        if not articles:
            if len(text) <= self.max_chunk_size:
                return [self._chunk_with_metadata(text, "document", metadata)]
            return self._fallback_chunking(text, metadata)

        chunks: List[LegalChunk] = []
        preamble = text[: articles[0]["start"]].strip()
        if len(preamble) >= self.min_chunk_size:
            chunks.append(self._chunk_with_metadata(preamble, "preamble", metadata))

        for article in articles:
            article_text = text[article["start"]: article["end"]].strip()
            chapter = self._find_context_for_position(text, article["start"], "chapter")
            section = self._find_context_for_position(text, article["start"], "section")

            if len(article_text) <= self.max_chunk_size:
                chunks.append(
                    self._chunk_with_metadata(
                        article_text,
                        "article",
                        metadata,
                        article_number=article["number"],
                        chapter=chapter,
                        section=section,
                    )
                )
            else:
                chunks.extend(
                    self._split_article_into_clauses(
                        article_text,
                        article["number"],
                        metadata,
                        chapter,
                        section,
                    )
                )

        return chunks

    def _fallback_chunking(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_type: str = "paragraph",
        article_number: Optional[str] = None,
        clause_number: Optional[str] = None,
        point_number: Optional[str] = None,
        chapter: Optional[str] = None,
        section: Optional[str] = None,
    ) -> List[LegalChunk]:
        """Fallback paragraph chunking with optional character overlap."""
        paragraphs = [para.strip() for para in text.split("\n\n") if para.strip()]
        chunks: List[LegalChunk] = []
        current: List[str] = []
        current_length = 0
        overlap_text = ""

        def emit_current() -> None:
            nonlocal current, current_length, overlap_text
            if not current:
                return
            content = "\n\n".join(current).strip()
            if content:
                chunks.append(
                    self._chunk_with_metadata(
                        content,
                        chunk_type,
                        metadata,
                        article_number=article_number,
                        clause_number=clause_number,
                        point_number=point_number,
                        chapter=chapter,
                        section=section,
                    )
                )
                overlap_text = content[-self.chunk_overlap :] if self.chunk_overlap else ""
            current = [overlap_text] if overlap_text else []
            current_length = len(overlap_text)

        for paragraph in paragraphs:
            if current_length and current_length + len(paragraph) + 2 > self.max_chunk_size:
                emit_current()

            if len(paragraph) > self.max_chunk_size:
                start = 0
                while start < len(paragraph):
                    end = start + self.max_chunk_size
                    part = paragraph[start:end].strip()
                    if part:
                        chunks.append(
                            self._chunk_with_metadata(
                                part,
                                chunk_type,
                                metadata,
                                article_number=article_number,
                                clause_number=clause_number,
                                point_number=point_number,
                                chapter=chapter,
                                section=section,
                            )
                        )
                    if end >= len(paragraph):
                        break
                    start = max(end - self.chunk_overlap, start + 1)
                current = []
                current_length = 0
                overlap_text = ""
                continue

            current.append(paragraph)
            current_length += len(paragraph) + 2

        emit_current()
        return chunks
