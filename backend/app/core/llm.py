"""
LLM Service Module
Google Gemini integration for generating responses
"""
from typing import Optional, List, Dict, Any, Generator
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class LLMService:
    """
    LLM service using Google Gemini for Vietnamese legal Q&A
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        
        # Configure Gemini
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        self._model = None
    
    @property
    def model(self):
        """Lazy load the model"""
        if self._model is None:
            # Ensure model name has correct format
            model_name = self.model_name
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            
            self._model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )
        return self._model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context
        
        Returns:
            Generated response text
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.model.generate_content(full_prompt)
        
        if response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        
        return "Xin lỗi, tôi không thể tạo câu trả lời. Vui lòng thử lại."
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response
        
        Yields:
            Text chunks as they are generated
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.model.generate_content(full_prompt, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text"""
        return self.model.count_tokens(text).total_tokens


# Singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


if __name__ == "__main__":
    # Test the LLM service (requires API key)
    import os
    
    if os.getenv("GEMINI_API_KEY"):
        service = LLMService()
        response = service.generate(
            "Xin chào, bạn là ai?",
            system_prompt="Bạn là trợ lý pháp luật Việt Nam."
        )
        print(response)
    else:
        print("GEMINI_API_KEY not set. Skipping test.")
