from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.knowledge.repository import KnowledgeRepository


def test_knowledge_repository_persists_document_chunks_and_trace():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        repository = KnowledgeRepository(session)
        document = repository.create_document(
            title="Payments",
            source_type="manual",
            source_name="seed",
            content_hash="abc",
            metadata_json={"team": "Payment Team"},
        )
        chunks = repository.replace_chunks(document, [(0, "Payment context", 15, {"team": "Payment Team"})])
        repository.update_chunk_point_id(chunks[0], qdrant_point_id="point-1")
        trace = repository.create_retrieval_trace(
            feedback_record_id=None,
            query_text="payment failed",
            provider="qdrant",
            embedding_model="BAAI/bge-m3",
            collection_name="feedbackiq_knowledge",
            top_k=3,
            filters_json={"team": "Payment Team"},
        )
        item = repository.add_trace_item(
            trace,
            knowledge_chunk_id=chunks[0].id,
            qdrant_point_id="point-1",
            score=0.9,
            rank=1,
            text_preview="Payment context",
            metadata_json={"team": "Payment Team"},
        )
        session.commit()

        loaded = repository.get_document(document.id)

    assert loaded is not None
    assert len(loaded.chunks) == 1
    assert loaded.chunks[0].qdrant_point_id == "point-1"
    assert item.rank == 1
