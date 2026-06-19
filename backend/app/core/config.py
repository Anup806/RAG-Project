from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "PDF Knowledge Assistant"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    GOOGLE_API_KEY: str = ""
    GOOGLE_LLM_MODEL: str = "gemma-4-26b-a4b-it"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GOOGLE_EMBEDDING_DIMENSIONS: int = 768
    GOOGLE_TEMPERATURE: float = 0.2
    GOOGLE_MAX_OUTPUT_TOKENS: int = 1600

    DATABASE_URL: str = "postgresql+asyncpg://rag:rag@postgres:5432/rag"

    CHROMA_PATH: str = "./data/chroma"
    CHROMA_HOST: str | None = None
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "pdf_chunks"

    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 25
    MAX_FILES_PER_UPLOAD: int = 10

    CHUNK_SIZE_TOKENS: int = Field(default=700, ge=500, le=800)
    CHUNK_OVERLAP_TOKENS: int = Field(default=120, ge=100, le=150)

    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    SEMANTIC_WEIGHT: float = 0.65
    KEYWORD_WEIGHT: float = 0.35

    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    DEFAULT_USER_EMAIL: str = "demo@example.com"
    DEFAULT_USER_NAME: str = "Demo User"

    CORS_ORIGINS: Annotated[list[str], BeforeValidator(_split_csv)] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = Path(self.CHROMA_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

