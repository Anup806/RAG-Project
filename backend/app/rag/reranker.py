import asyncio
import logging
from abc import ABC, abstractmethod

from app.core.config import settings
from app.rag.models import RetrievedChunk

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError


class ScoreFallbackReranker(BaseReranker):
    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        return sorted(chunks, key=lambda item: item.score, reverse=True)[:top_k]


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str = settings.RERANKER_MODEL, enabled: bool = settings.RERANKER_ENABLED) -> None:
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self._fallback = ScoreFallbackReranker()

    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if not chunks:
            return []
        if not self.enabled:
            return await self._fallback.rerank(query, chunks, top_k)
        try:
            return await asyncio.to_thread(self._rerank_sync, query, chunks, top_k)
        except Exception:
            logger.exception("CrossEncoder reranking failed; falling back to hybrid scores.")
            return await self._fallback.rerank(query, chunks, top_k)

    def _rerank_sync(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        pairs = [(query, chunk.text) for chunk in chunks]
        scores = self._model.predict(pairs)
        for chunk, score in zip(chunks, scores, strict=False):
            chunk.rerank_score = float(score)
        return sorted(
            chunks,
            key=lambda item: item.rerank_score if item.rerank_score is not None else item.score,
            reverse=True,
        )[:top_k]

