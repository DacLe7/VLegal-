"""
Configuration module for V-Legal Bot
Loads settings from environment variables with validation
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv
import os


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


# Find and load .env file
def _find_env_file():
    """Find .env file starting from current dir up to project root"""
    current = Path.cwd()
    for _ in range(5):  # Max 5 levels up
        env_file = current / ".env"
        if env_file.exists():
            return str(env_file)
        current = current.parent
    return ".env"


# Load environment variables
load_dotenv(_find_env_file())


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Info
    app_name: str = Field(default="V-Legal RAG Demo")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Google Gemini API
    gemini_api_key: str = Field(default="")
    
    # Vector Database
    chroma_persist_dir: str = Field(default="./vectordb")
    chroma_collection_name: str = Field(default="legal_documents")
    
    # Document Processing
    data_dir: str = Field(default="./Data")
    chunk_size: int = Field(default=1800)
    chunk_overlap: int = Field(default=150)
    
    # Embeddings
    embedding_model: str = Field(default="intfloat/multilingual-e5-small")
    
    # LLM Settings
    llm_model: str = Field(default="gemini-2.5-flash")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=4096)
    
    # Retrieval Settings
    retrieval_top_k: int = Field(default=8)
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()
    
    @property
    def vectordb_path(self) -> Path:
        return Path(self.chroma_persist_dir).resolve()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
