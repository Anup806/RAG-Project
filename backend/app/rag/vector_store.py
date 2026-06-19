import asyncio
import logging
from collections.abc import Iterable

import chromadb

from app.core.config import settings
from app.rag.models import RAGChunk, RetrievedChunk

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self) -> None:
        if settings.CHROMA_HOST:
            self.client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        else:
            self.client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_chunks(self, chunks: list[RAGChunk], embeddings: list[list[float]]) -> None:
        await asyncio.to_thread(self._add_chunks, chunks, embeddings)

    def _add_chunks(self, chunks: list[RAGChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata() for chunk in chunks],
        )

    async def semantic_search(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        return await asyncio.to_thread(self._semantic_search, query_embedding, top_k, document_ids)

    def _semantic_search(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None,
    ) -> list[RetrievedChunk]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=self._document_filter(document_ids),
            include=["documents", "metadatas", "distances"],
        )
        chunks: list[RetrievedChunk] = []
        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for chunk_id, metadata, document, distance in zip(ids, metadatas, documents, distances, strict=False):
            score = max(0.0, 1.0 - float(distance))
            chunks.append(
                RetrievedChunk(
                    filename=str(metadata["filename"]),
                    document_id=str(metadata["document_id"]),
                    page_number=int(metadata["page_number"]),
                    chunk_id=str(metadata.get("chunk_id", chunk_id)),
                    text=str(document or metadata.get("text", "")),
                    semantic_score=score,
                    score=score,
                )
            )
        return chunks

    async def get_chunks(self, document_ids: list[str] | None = None) -> list[RAGChunk]:
        return await asyncio.to_thread(self._get_chunks, document_ids)

    def _get_chunks(self, document_ids: list[str] | None = None) -> list[RAGChunk]:
        result = self.collection.get(
            where=self._document_filter(document_ids),
            include=["documents", "metadatas"],
        )
        chunks: list[RAGChunk] = []
        for chunk_id, metadata, document in zip(
            result.get("ids", []),
            result.get("metadatas", []),
            result.get("documents", []),
            strict=False,
        ):
            chunks.append(
                RAGChunk(
                    filename=str(metadata["filename"]),
                    document_id=str(metadata["document_id"]),
                    page_number=int(metadata["page_number"]),
                    chunk_id=str(metadata.get("chunk_id", chunk_id)),
                    text=str(document or metadata.get("text", "")),
                )
            )
        return chunks

    async def delete_document(self, document_id: str) -> None:
        await asyncio.to_thread(self.collection.delete, where={"document_id": document_id})

    async def heartbeat(self) -> bool:
        try:
            await asyncio.to_thread(self.client.heartbeat)
            return True
        except Exception:
            logger.exception("Chroma heartbeat failed")
            return False

    def _document_filter(self, document_ids: Iterable[str] | None) -> dict | None:
        ids = [doc_id for doc_id in (document_ids or []) if doc_id]
        if not ids:
            return None
        if len(ids) == 1:
            return {"document_id": ids[0]}
        return {"document_id": {"$in": ids}}

