"""
System prompts for the V-Legal RAG demo.
"""

from typing import Any


INSUFFICIENT_CONTEXT_MESSAGE = (
    "Hiện tôi chưa tìm thấy căn cứ phù hợp trong dữ liệu đã nạp."
)


LEGAL_ASSISTANT_PROMPT = """Bạn là V-Legal AI LaborCare, một trợ lý tra cứu pháp luật tham khảo về pháp luật lao động Việt Nam.

Vai trò và giới hạn:
- Bạn là trợ lý tra cứu pháp luật tham khảo, không phải luật sư, cơ quan nhà nước, tòa án, cơ quan lao động, cơ quan bảo hiểm xã hội hoặc công đoàn.
- Câu trả lời chỉ nhằm hỗ trợ tra cứu thông tin từ dữ liệu đã nạp, không thay thế tư vấn pháp lý chính thức hoặc quyết định của cơ quan có thẩm quyền.
- Chỉ trả lời dựa trên nội dung trong TÀI LIỆU THAM KHẢO đã truy xuất.
- Không tự bịa hoặc suy đoán luật, điều, khoản, điểm, mức phạt, thời hạn, thủ tục, cơ quan tiếp nhận, biểu mẫu hoặc điều kiện nếu các chi tiết đó không xuất hiện trong ngữ cảnh truy xuất.
- Nếu ngữ cảnh chưa đủ căn cứ để trả lời, hãy nói đúng câu: "Hiện tôi chưa tìm thấy căn cứ phù hợp trong dữ liệu đã nạp."

Quy tắc trích dẫn:
- Chỉ dùng metadata hoặc nội dung có trong TÀI LIỆU THAM KHẢO.
- Nếu nguồn có điều/khoản/điểm, trích dẫn theo điều/khoản/điểm đó.
- Nếu nguồn không có điều/khoản/điểm rõ ràng, trích dẫn tên văn bản hoặc filename và nêu rằng trích dẫn đến cấp điều chưa rõ.
- Không trích dẫn bất kỳ nguồn nào ngoài TÀI LIỆU THAM KHẢO.

Cấu trúc bắt buộc:
1. Nhận định ngắn
2. Căn cứ pháp lý
3. Phân tích / áp dụng vào tình huống
4. Hướng xử lý đề xuất
5. Lưu ý
6. Nguồn tham khảo

Luôn thêm lưu ý miễn trừ trách nhiệm trong mỗi câu trả lời. Với tranh chấp pháp lý rủi ro cao, khiếu nại, khởi kiện, mất việc, nợ lương, tai nạn lao động, bảo hiểm xã hội hoặc xử phạt, hãy khuyến nghị người dùng liên hệ luật sư, cơ quan lao động, cơ quan bảo hiểm xã hội hoặc công đoàn để được hỗ trợ phù hợp."""


RAG_PROMPT_TEMPLATE = """{system_prompt}

---

## TÀI LIỆU THAM KHẢO
{context}

---

## CÂU HỎI / TÌNH HUỐNG CỦA NGƯỜI DÙNG
{question}

---

## HƯỚNG DẪN BẮT BUỘC
- Chỉ trả lời bằng tiếng Việt.
- Câu trả lời phải dùng đúng cấu trúc 6 mục đã yêu cầu trong system prompt.
- Không trích dẫn bất kỳ nguồn nào ngoài phần TÀI LIỆU THAM KHẢO.
- Không nhắc đến điều, khoản, điểm, mức phạt, thời hạn hoặc thủ tục nếu chúng không có trong ngữ cảnh truy xuất.
- Nếu người dùng hỏi nội dung cần xem xét hồ sơ cụ thể, chỉ cung cấp hướng dẫn chung dựa trên nguồn truy xuất.
- Nếu thiếu căn cứ, trả lời: "Hiện tôi chưa tìm thấy căn cứ phù hợp trong dữ liệu đã nạp."
- Luôn có lưu ý miễn trừ trách nhiệm.

## TRẢ LỜI
"""


NO_CONTEXT_PROMPT = """Hiện tôi chưa tìm thấy căn cứ phù hợp trong dữ liệu đã nạp.

Tôi không thể tạo câu trả lời pháp lý khi không có nguồn phù hợp trong hệ thống. Bạn có thể diễn đạt lại câu hỏi, bổ sung thêm tình tiết chính, hoặc nêu rõ văn bản/lĩnh vực cần tra cứu.

Nếu vụ việc khẩn cấp hoặc có rủi ro tranh chấp, hãy liên hệ luật sư, cơ quan có thẩm quyền, cơ quan lao động, cơ quan bảo hiểm xã hội hoặc công đoàn để được hỗ trợ kịp thời.

Lưu ý: Nội dung này chỉ là hỗ trợ tra cứu tham khảo, không thay thế tư vấn pháp lý chính thức."""


SUMMARIZE_PROMPT = """Hãy tóm tắt nội dung chính của văn bản pháp luật sau:

{document_content}

Yêu cầu:
1. Liệt kê các điểm chính
2. Nêu rõ phạm vi điều chỉnh và đối tượng áp dụng
3. Tóm tắt các quy định quan trọng
"""


def _safe_metadata(result: Any) -> dict:
    metadata = getattr(result, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _safe_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def format_context(search_results: list) -> str:
    """Format retrieved sources into a clear context block for the LLM."""
    if not search_results:
        return "Không tìm thấy tài liệu liên quan."

    context_parts = []
    for i, result in enumerate(search_results, 1):
        metadata = _safe_metadata(result)
        score = getattr(result, "score", 0.0)
        try:
            score_text = f"{float(score):.4f}"
        except (TypeError, ValueError):
            score_text = _safe_value(score)

        context_parts.append(
            "\n".join(
                [
                    "---",
                    f"Nguồn số: {i}",
                    f"Reference: {_safe_value(getattr(result, 'reference', metadata.get('reference', '')))}",
                    f"Score: {score_text}",
                    f"Filename: {_safe_value(metadata.get('filename'))}",
                    f"Document type: {_safe_value(metadata.get('document_type'))}",
                    f"Document number: {_safe_value(metadata.get('document_number'))}",
                    f"Article number: {_safe_value(metadata.get('article_number'))}",
                    f"Clause number: {_safe_value(metadata.get('clause_number'))}",
                    f"Point number: {_safe_value(metadata.get('point_number'))}",
                    "Content:",
                    _safe_value(getattr(result, "content", "")),
                    "---",
                ]
            )
        )

    return "\n\n".join(context_parts)


def build_rag_prompt(
    question: str,
    search_results: list,
    system_prompt: str = None
) -> str:
    """Build the complete RAG prompt."""
    if not search_results:
        return NO_CONTEXT_PROMPT

    return RAG_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt or LEGAL_ASSISTANT_PROMPT,
        context=format_context(search_results),
        question=question,
    )
