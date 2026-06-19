import asyncio
import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleEmbeddingClient:
    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set; embedding calls will fail until configured.")
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY or None)
        self.model = settings.GOOGLE_EMBEDDING_MODEL

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed, texts, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._embed, [text], "RETRIEVAL_QUERY")
        return vectors[0]

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.GOOGLE_EMBEDDING_DIMENSIONS,
            ),
        )
        return [embedding.values for embedding in response.embeddings]

