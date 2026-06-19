from app.core.config import settings
from app.rag.embeddings import GoogleEmbeddingClient
from app.rag.keyword import BM25Retriever
from app.rag.models import RetrievedChunk
from app.rag.vector_store import ChromaVectorStore


class HybridRetriever:
    def __init__(
        self,
        embeddings: GoogleEmbeddingClient,
        vector_store: ChromaVectorStore,
        keyword_retriever: BM25Retriever,
    ) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.keyword_retriever = keyword_retriever

    async def retrieve(
        self,
        query: str,
        top_k: int = settings.RETRIEVAL_TOP_K,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = await self.embeddings.embed_query(query)
        semantic = await self.vector_store.semantic_search(query_embedding, top_k=top_k, document_ids=document_ids)
        all_chunks = await self.vector_store.get_chunks(document_ids=document_ids)
        keyword = self.keyword_retriever.search(query, all_chunks, top_k=top_k)

        merged: dict[str, RetrievedChunk] = {}
        for chunk in semantic:
            merged[chunk.chunk_id] = chunk
        for chunk in keyword:
            current = merged.get(chunk.chunk_id)
            if current:
                current.keyword_score = max(current.keyword_score, chunk.keyword_score)
            else:
                merged[chunk.chunk_id] = chunk

        for chunk in merged.values():
            chunk.score = (
                settings.SEMANTIC_WEIGHT * chunk.semantic_score
                + settings.KEYWORD_WEIGHT * chunk.keyword_score
            )

        results = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        return results[:top_k]

