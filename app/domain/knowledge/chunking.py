from dataclasses import dataclass

from app.core.exceptions import BadRequestError


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    char_count: int


class TextChunker:
    def __init__(self, *, chunk_size_chars: int, overlap_chars: int) -> None:
        if overlap_chars >= chunk_size_chars:
            raise ValueError("overlap_chars must be smaller than chunk_size_chars.")
        self.chunk_size_chars = chunk_size_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[TextChunk]:
        normalized = text.strip()
        if not normalized:
            raise BadRequestError("Knowledge document text cannot be empty.")
        chunks: list[TextChunk] = []
        start = 0
        while start < len(normalized):
            end = min(start + self.chunk_size_chars, len(normalized))
            chunk_text = normalized[start:end].strip()
            if chunk_text:
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        text=chunk_text,
                        char_count=len(chunk_text),
                    )
                )
            if end == len(normalized):
                break
            start = max(end - self.overlap_chars, start + 1)
        return chunks
