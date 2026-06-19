from functools import lru_cache

from app.rag.embeddings import GoogleEmbeddingClient
from app.rag.keyword import BM25Retriever
from app.rag.pipeline import RAGPipeline
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import ChromaVectorStore
from app.services.google_llm import GoogleLLMClient


@lru_cache
def get_embedding_client() -> GoogleEmbeddingClient:
    return GoogleEmbeddingClient()


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore()


@lru_cache
def get_rag_pipeline() -> RAGPipeline:
    vector_store = get_vector_store()
    embeddings = get_embedding_client()
    retriever = HybridRetriever(embeddings, vector_store, BM25Retriever())
    reranker = CrossEncoderReranker()
    return RAGPipeline(retriever, reranker, GoogleLLMClient())

