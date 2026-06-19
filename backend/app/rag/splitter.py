import re
from collections.abc import Iterable

from app.core.config import settings
from app.rag.models import PageText, RAGChunk


class RecursiveTokenTextSplitter:
    """Recursive splitter that keeps chunks inside the configured token budget."""

    separators = ("\n\n", "\n", ". ", "; ", ", ", " ")
    token_re = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE_TOKENS,
        chunk_overlap: int = settings.CHUNK_OVERLAP_TOKENS,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_pages(self, pages: Iterable[PageText], filename: str, document_id: str) -> list[RAGChunk]:
        chunks: list[RAGChunk] = []
        counter = 0
        for page in pages:
            for text in self.split_text(page.text):
                counter += 1
                chunk_id = f"{document_id}:p{page.page_number}:c{counter}"
                chunks.append(
                    RAGChunk(
                        filename=filename,
                        document_id=document_id,
                        page_number=page.page_number,
                        chunk_id=chunk_id,
                        text=text,
                    )
                )
        return chunks

    def split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []
        pieces = self._recursive_split(text, 0)
        return self._merge_with_overlap([piece for piece in pieces if piece.strip()])

    def _recursive_split(self, text: str, separator_index: int) -> list[str]:
        if self._token_count(text) <= self.chunk_size:
            return [text.strip()]
        if separator_index >= len(self.separators):
            return self._hard_split(text)

        separator = self.separators[separator_index]
        parts = text.split(separator)
        if len(parts) == 1:
            return self._recursive_split(text, separator_index + 1)

        splits: list[str] = []
        buffer = ""
        for part in parts:
            candidate = part if not buffer else f"{buffer}{separator}{part}"
            if self._token_count(candidate) <= self.chunk_size:
                buffer = candidate
                continue
            if buffer:
                splits.extend(self._recursive_split(buffer, separator_index + 1))
            buffer = part
        if buffer:
            splits.extend(self._recursive_split(buffer, separator_index + 1))
        return splits

    def _hard_split(self, text: str) -> list[str]:
        tokens = self.tokenize(text)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunks.append(" ".join(tokens[start:end]))
            if end == len(tokens):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks

    def _merge_with_overlap(self, pieces: list[str]) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_count = 0

        for piece in pieces:
            piece_count = self._token_count(piece)
            if current and current_count + piece_count > self.chunk_size:
                chunks.append(" ".join(current).strip())
                current = self._overlap_tokens(current)
                current_count = self._token_count(" ".join(current))
            current.append(piece)
            current_count += piece_count

        if current:
            chunks.append(" ".join(current).strip())
        return chunks

    def _overlap_tokens(self, pieces: list[str]) -> list[str]:
        tokens = self.tokenize(" ".join(pieces))
        if not tokens:
            return []
        return [" ".join(tokens[-self.chunk_overlap :])]

    def tokenize(self, text: str) -> list[str]:
        return self.token_re.findall(text)

    def _token_count(self, text: str) -> int:
        return len(self.tokenize(text))

