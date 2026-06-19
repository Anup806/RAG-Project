from dataclasses import dataclass, field


@dataclass(slots=True)
class PageText:
    page_number: int
    text: str


@dataclass(slots=True)
class RAGChunk:
    filename: str
    document_id: str
    page_number: int
    chunk_id: str
    text: str

    def metadata(self) -> dict[str, str | int]:
        return {
            "filename": self.filename,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "text": self.text,
        }


@dataclass(slots=True)
class RetrievedChunk(RAGChunk):
    score: float = 0.0
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float | None = None

    @classmethod
    def from_chunk(cls, chunk: RAGChunk, **scores: float | None) -> "RetrievedChunk":
        return cls(
            filename=chunk.filename,
            document_id=chunk.document_id,
            page_number=chunk.page_number,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            score=float(scores.get("score") or 0.0),
            semantic_score=float(scores.get("semantic_score") or 0.0),
            keyword_score=float(scores.get("keyword_score") or 0.0),
            rerank_score=scores.get("rerank_score"),
        )

    def citation(self) -> dict[str, str | int]:
        return self.metadata()


@dataclass(slots=True)
class RAGResult:
    answer: str
    sources: list[dict[str, str | int]] = field(default_factory=list)

