from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.knowledge.models import KnowledgeChunk, KnowledgeDocument, RetrievalTrace, RetrievalTraceItem


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_document(
        self,
        *,
        title: str,
        source_type: str,
        source_name: str | None,
        content_hash: str,
        metadata_json: dict | None,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            title=title,
            source_type=source_type,
            source_name=source_name,
            content_hash=content_hash,
            metadata_json=metadata_json,
        )
        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document

    def get_document(self, document_id: int) -> KnowledgeDocument | None:
        return self.session.scalar(
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .where(KnowledgeDocument.id == document_id)
        )

    def list_documents(self, *, limit: int, offset: int) -> list[KnowledgeDocument]:
        return list(
            self.session.scalars(
                select(KnowledgeDocument)
                .order_by(KnowledgeDocument.created_at.desc(), KnowledgeDocument.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def replace_chunks(
        self,
        document: KnowledgeDocument,
        chunks: Sequence[tuple[int, str, int, dict | None]],
    ) -> list[KnowledgeChunk]:
        document.chunks.clear()
        self.session.flush()
        created: list[KnowledgeChunk] = []
        for chunk_index, text, char_count, metadata_json in chunks:
            chunk = KnowledgeChunk(
                chunk_index=chunk_index,
                text=text,
                char_count=char_count,
                metadata_json=metadata_json,
            )
            document.chunks.append(chunk)
            created.append(chunk)
        self.session.flush()
        for chunk in created:
            self.session.refresh(chunk)
        return created

    def update_chunk_point_id(self, chunk: KnowledgeChunk, *, qdrant_point_id: str) -> KnowledgeChunk:
        chunk.qdrant_point_id = qdrant_point_id
        self.session.flush()
        self.session.refresh(chunk)
        return chunk

    def create_retrieval_trace(
        self,
        *,
        feedback_record_id: int | None,
        query_text: str,
        provider: str,
        embedding_model: str,
        collection_name: str | None,
        top_k: int,
        filters_json: dict | None,
    ) -> RetrievalTrace:
        trace = RetrievalTrace(
            feedback_record_id=feedback_record_id,
            query_text=query_text,
            provider=provider,
            embedding_model=embedding_model,
            collection_name=collection_name,
            top_k=top_k,
            filters_json=filters_json,
        )
        self.session.add(trace)
        self.session.flush()
        self.session.refresh(trace)
        return trace

    def add_trace_item(
        self,
        trace: RetrievalTrace,
        *,
        knowledge_chunk_id: int | None,
        qdrant_point_id: str | None,
        score: float,
        rank: int,
        text_preview: str,
        metadata_json: dict | None,
    ) -> RetrievalTraceItem:
        item = RetrievalTraceItem(
            retrieval_trace_id=trace.id,
            knowledge_chunk_id=knowledge_chunk_id,
            qdrant_point_id=qdrant_point_id,
            score=score,
            rank=rank,
            text_preview=text_preview,
            metadata_json=metadata_json,
        )
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item
