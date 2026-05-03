from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.vector_store import SearchResult


def test_builds_query_and_context():
    context = RagContextBuilder().build(
        "payment failed",
        [
            SearchResult(text="The Payment Team improved checkout.", score=0.9),
            SearchResult(text="The Support Team reduced tickets.", score=0.7),
        ],
    )

    assert "Query: payment failed" in context
    assert "The Payment Team improved checkout." in context
    assert "The Support Team reduced tickets." in context

