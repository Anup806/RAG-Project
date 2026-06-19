import math
import re

from rank_bm25 import BM25Okapi

from app.rag.models import RAGChunk, RetrievedChunk


class BM25Retriever:
    token_re = re.compile(r"\w+", re.UNICODE)

    def search(self, query: str, chunks: list[RAGChunk], top_k: int) -> list[RetrievedChunk]:
        if not chunks:
            return []
        corpus = [self._tokenize(chunk.text) for chunk in chunks]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
        max_score = max(float(score) for score in scores) if len(scores) else 0.0
        ranked: list[RetrievedChunk] = []
        for chunk, score in zip(chunks, scores, strict=False):
            raw_score = float(score)
            normalized = raw_score / max_score if max_score > 0 else 0.0
            if math.isfinite(normalized) and normalized > 0:
                ranked.append(
                    RetrievedChunk.from_chunk(
                        chunk,
                        keyword_score=normalized,
                        score=normalized,
                    )
                )
        ranked.sort(key=lambda item: item.keyword_score, reverse=True)
        return ranked[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in self.token_re.findall(text)]

