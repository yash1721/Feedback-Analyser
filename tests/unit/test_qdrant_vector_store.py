from app.domain.retrieval.qdrant_vector_store import QdrantVectorStore


def test_qdrant_filter_supports_equality_and_list_values():
    store = QdrantVectorStore(
        url="http://localhost:6333",
        collection_name="test",
        vector_size=3,
    )

    qdrant_filter = store._build_filter({"team": "Payment Team", "tags": ["billing", "checkout"]})

    assert qdrant_filter is not None
    assert len(qdrant_filter.must) == 2
