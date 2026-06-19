from collections.abc import AsyncGenerator

from app.core.config import settings
from app.rag.prompt import append_source_footer, build_rag_prompt, format_sources
from app.rag.reranker import BaseReranker
from app.rag.retriever import HybridRetriever
from app.services.google_llm import GoogleLLMClient


class RAGPipeline:
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: BaseReranker,
        llm: GoogleLLMClient,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm

    async def retrieve_context(self, question: str, document_ids: list[str] | None = None):
        retrieved = await self.retriever.retrieve(
            question,
            top_k=settings.RETRIEVAL_TOP_K,
            document_ids=document_ids,
        )
        return await self.reranker.rerank(question, retrieved, top_k=settings.RERANK_TOP_K)

    async def stream_answer(
        self,
        question: str,
        document_ids: list[str] | None = None,
    ) -> AsyncGenerator[tuple[str, list[dict[str, str | int]]], None]:
        chunks = await self.retrieve_context(question, document_ids=document_ids)
        sources = [chunk.citation() for chunk in chunks]
        if not chunks:
            yield (
                "The uploaded documents do not contain enough information to answer that question.\n\n"
                f"{format_sources(sources)}",
                sources,
            )
            return

        prompt = build_rag_prompt(question, chunks)
        async for token in self.llm.stream(prompt):
            yield token, sources
        yield f"\n\n{format_sources(sources)}", sources

    async def answer(self, question: str, document_ids: list[str] | None = None) -> tuple[str, list[dict[str, str | int]]]:
        chunks = await self.retrieve_context(question, document_ids=document_ids)
        sources = [chunk.citation() for chunk in chunks]
        if not chunks:
            return (
                "The uploaded documents do not contain enough information to answer that question.\n\n"
                f"{format_sources(sources)}",
                sources,
            )
        answer = await self.llm.complete(build_rag_prompt(question, chunks))
        return append_source_footer(answer, sources), sources

