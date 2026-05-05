from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.core.metrics import RETRIEVAL_LATENCY_SECONDS, RETRIEVAL_NO_RESULT_TOTAL, RETRIEVAL_REQUESTS_TOTAL, Timer
from app.domain.knowledge.service import KnowledgeService
from app.domain.retrieval.embedding_model import EmbeddingModel
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.vector_store import SearchResult, VectorStore


@dataclass(frozen=True)
class RetrievalSearchResult:
    results: list[SearchResult]
    rag_context: str
    trace_id: int | None = None


class RetrievalService:
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        context_builder: RagContextBuilder,
        knowledge_base: list[str],
        settings: Settings | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.context_builder = context_builder
        self.knowledge_base = knowledge_base
        self.settings = settings
        self.knowledge_service = knowledge_service
        self._initialized = False

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        return self.search_with_options(query, top_k=top_k).results

    def build_context(self, query: str, top_k: int) -> tuple[list[SearchResult], str]:
        result = self.search_with_options(query, top_k=top_k)
        return result.results, result.rag_context

    def search_with_options(
        self,
        query: str,
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
        persist_trace: bool = False,
        feedback_record_id: int | None = None,
    ) -> RetrievalSearchResult:
        provider = self.settings.vector_provider if self.settings is not None else self.vector_store.__class__.__name__
        timer = Timer()
        try:
            self._ensure_initialized()
            query_embedding = self.embedding_model.embed([query])
            results = self.vector_store.search_with_filters(query_embedding, top_k=top_k, filters=filters)
            rag_context = self.context_builder.build(query, results)
            trace_id = None
            if persist_trace and self.knowledge_service is not None:
                trace = self.knowledge_service.persist_retrieval_trace(
                    query_text=query,
                    results=results,
                    top_k=top_k,
                    filters=filters,
                    feedback_record_id=feedback_record_id,
                )
                trace_id = trace.id
            RETRIEVAL_REQUESTS_TOTAL.labels(provider=provider, status="success").inc()
            if not results:
                RETRIEVAL_NO_RESULT_TOTAL.labels(provider=provider).inc()
            return RetrievalSearchResult(results=results, rag_context=rag_context, trace_id=trace_id)
        except Exception:
            RETRIEVAL_REQUESTS_TOTAL.labels(provider=provider, status="failed").inc()
            raise
        finally:
            RETRIEVAL_LATENCY_SECONDS.labels(provider=provider).observe(timer.elapsed())

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if self.settings is not None and self.settings.vector_provider == "qdrant":
            self.vector_store.ensure_collection()
            self._initialized = True
            return
        embeddings = self.embedding_model.embed(self.knowledge_base)
        self.vector_store.add_texts(self.knowledge_base, embeddings)
        self._initialized = True
