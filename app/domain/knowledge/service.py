from hashlib import sha256

from app.config import Settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.metrics import PROMPT_INJECTION_DETECTED_TOTAL
from app.domain.guardrails.prompt_injection import PromptInjectionDetector, PromptInjectionRisk
from app.domain.knowledge.chunking import TextChunker
from app.domain.knowledge.models import KnowledgeDocument, RetrievalTrace
from app.domain.knowledge.repository import KnowledgeRepository
from app.domain.retrieval.embedding_model import EmbeddingModel
from app.domain.retrieval.vector_store import SearchResult, VectorChunk, VectorStore


class KnowledgeService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        settings: Settings,
        prompt_injection_detector: PromptInjectionDetector | None = None,
    ) -> None:
        self.repository = repository
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.settings = settings
        self.prompt_injection_detector = prompt_injection_detector or PromptInjectionDetector()
        self.chunker = TextChunker(
            chunk_size_chars=settings.knowledge_chunk_size_chars,
            overlap_chars=settings.knowledge_chunk_overlap_chars,
        )

    def create_document(
        self,
        *,
        title: str,
        text: str,
        source_type: str,
        source_name: str | None,
        metadata: dict | None,
    ) -> KnowledgeDocument:
        if self.settings.prompt_injection_detection_enabled:
            injection = self.prompt_injection_detector.detect(text)
            if injection.detected:
                PROMPT_INJECTION_DETECTED_TOTAL.labels(risk_level=injection.risk_level.value).inc()
                if self.settings.prompt_injection_mode == "block" and injection.risk_level == PromptInjectionRisk.HIGH:
                    raise BadRequestError("Knowledge document contains high-risk prompt-injection instructions.")
        document = self.repository.create_document(
            title=title,
            source_type=source_type,
            source_name=source_name,
            content_hash=sha256(text.encode("utf-8")).hexdigest(),
            metadata_json={**(metadata or {}), "text": text},
        )
        self.repository.session.commit()
        return document

    def list_documents(self, *, limit: int, offset: int) -> list[KnowledgeDocument]:
        return self.repository.list_documents(limit=limit, offset=offset)

    def get_document(self, document_id: int) -> KnowledgeDocument:
        document = self.repository.get_document(document_id)
        if document is None:
            raise NotFoundError("Knowledge document was not found.", {"document_id": document_id})
        return document

    def index_document(self, document_id: int) -> tuple[KnowledgeDocument, int]:
        document = self.get_document(document_id)
        text = (document.metadata_json or {}).get("text", "")
        chunks = self.chunker.chunk(str(text))
        persisted_chunks = self.repository.replace_chunks(
            document,
            [
                (
                    chunk.chunk_index,
                    chunk.text,
                    chunk.char_count,
                    self._chunk_metadata(document, chunk.chunk_index),
                )
                for chunk in chunks
            ],
        )
        embeddings = self.embedding_model.embed([chunk.text for chunk in persisted_chunks])
        vector_chunks = [
            VectorChunk(
                id=chunk.id,
                text=chunk.text,
                metadata={
                    **(chunk.metadata_json or {}),
                    "document_id": document.id,
                    "chunk_id": chunk.id,
                    "source_type": document.source_type,
                    "source_name": document.source_name,
                },
                point_id=chunk.qdrant_point_id,
            )
            for chunk in persisted_chunks
        ]
        upserted = self.vector_store.upsert_chunks(vector_chunks, embeddings)
        by_chunk_id = {item.chunk_id: item.point_id for item in upserted}
        for chunk in persisted_chunks:
            point_id = by_chunk_id.get(chunk.id)
            if point_id:
                self.repository.update_chunk_point_id(chunk, qdrant_point_id=point_id)
        self.repository.session.commit()
        return self.get_document(document_id), len(persisted_chunks)

    def persist_retrieval_trace(
        self,
        *,
        query_text: str,
        results: list[SearchResult],
        top_k: int,
        filters: dict | None,
        feedback_record_id: int | None,
    ) -> RetrievalTrace:
        trace = self.repository.create_retrieval_trace(
            feedback_record_id=feedback_record_id,
            query_text=query_text,
            provider=self.settings.vector_provider,
            embedding_model=self.settings.embedding_model_name,
            collection_name=self.settings.qdrant_collection_name if self.settings.vector_provider == "qdrant" else None,
            top_k=top_k,
            filters_json=filters,
        )
        for index, result in enumerate(results, start=1):
            self.repository.add_trace_item(
                trace,
                knowledge_chunk_id=result.chunk_id,
                qdrant_point_id=result.point_id,
                score=result.score,
                rank=result.rank or index,
                text_preview=result.text[:500],
                metadata_json=result.metadata,
            )
        self.repository.session.commit()
        self.repository.session.refresh(trace)
        return trace

    def _chunk_metadata(self, document: KnowledgeDocument, chunk_index: int) -> dict:
        metadata = dict(document.metadata_json or {})
        metadata.pop("text", None)
        metadata.update(
            {
                "document_id": document.id,
                "document_title": document.title,
                "chunk_index": chunk_index,
                "source_type": document.source_type,
                "source_name": document.source_name,
            }
        )
        return metadata
