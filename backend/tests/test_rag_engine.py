"""
Tests for RAG prompt generation.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.prompts import (  # noqa: E402
    LEGAL_ASSISTANT_PROMPT,
    NO_CONTEXT_PROMPT,
    build_rag_prompt,
    format_context,
)


class TestPrompts:
    def test_legal_prompt_exists(self):
        assert LEGAL_ASSISTANT_PROMPT is not None
        assert len(LEGAL_ASSISTANT_PROMPT) > 100
        assert "V-Legal AI LaborCare" in LEGAL_ASSISTANT_PROMPT
        assert "trợ lý tra cứu pháp luật tham khảo" in LEGAL_ASSISTANT_PROMPT
        assert "luật sư ảo" not in LEGAL_ASSISTANT_PROMPT.lower()

    def test_legal_prompt_has_key_elements(self):
        prompt = LEGAL_ASSISTANT_PROMPT.lower()
        assert "nguồn" in prompt or "trích dẫn" in prompt
        assert "chỉ trả lời dựa trên" in prompt
        assert "không thay thế" in prompt

    def test_no_context_prompt(self):
        assert NO_CONTEXT_PROMPT is not None
        assert "chưa tìm thấy căn cứ phù hợp" in NO_CONTEXT_PROMPT.lower()
        assert "không thể tạo câu trả lời pháp lý" in NO_CONTEXT_PROMPT.lower()

    def test_build_rag_prompt_with_results(self):
        class MockResult:
            content = "Điều 1. Nội dung điều 1."
            reference = "Điều 1, Luật Test"
            score = 0.95
            metadata = {
                "filename": "test.docx",
                "document_type": "Luật",
                "document_number": "01/TEST",
                "article_number": "1",
            }

        prompt = build_rag_prompt("Câu hỏi test?", [MockResult()])
        assert "Câu hỏi test?" in prompt
        assert "Điều 1" in prompt
        assert "Score: 0.9500" in prompt
        assert "Không trích dẫn bất kỳ nguồn nào ngoài phần TÀI LIỆU THAM KHẢO" in prompt

    def test_build_rag_prompt_no_results(self):
        prompt = build_rag_prompt("Câu hỏi test?", [])
        assert prompt == NO_CONTEXT_PROMPT


class TestFormatContext:
    def test_format_empty_results(self):
        result = format_context([])
        assert "không tìm thấy" in result.lower()

    def test_format_multiple_results(self):
        class MockResult:
            def __init__(self, num):
                self.content = f"Nội dung {num}"
                self.reference = f"Điều {num}"
                self.score = 0.9 - (num * 0.1)
                self.metadata = {"filename": f"test-{num}.docx", "article_number": str(num)}

        formatted = format_context([MockResult(1), MockResult(2)])
        assert "Nguồn số: 1" in formatted
        assert "Nguồn số: 2" in formatted
        assert "Article number: 1" in formatted
        assert "Article number: 2" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
