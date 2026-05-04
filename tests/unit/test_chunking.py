import pytest

from app.domain.knowledge.chunking import TextChunker


def test_text_chunker_applies_overlap():
    chunker = TextChunker(chunk_size_chars=10, overlap_chars=2)

    chunks = chunker.chunk("abcdefghijklmnopqrstuvwxyz")

    assert [chunk.text for chunk in chunks] == ["abcdefghij", "ijklmnopqr", "qrstuvwxyz"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]


def test_text_chunker_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        TextChunker(chunk_size_chars=10, overlap_chars=10)
