from app.domain.retrieval.embedding_model import EmbeddingModel
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.vector_store import SearchResult, VectorStore


class RetrievalService:
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        context_builder: RagContextBuilder,
        knowledge_base: list[str],
    ) -> None:
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.context_builder = context_builder
        self.knowledge_base = knowledge_base
        self._initialized = False

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        self._ensure_initialized()
        query_embedding = self.embedding_model.embed([query])
        return self.vector_store.search(query_embedding, top_k)

    def build_context(self, query: str, top_k: int) -> tuple[list[SearchResult], str]:
        results = self.search(query, top_k)
        return results, self.context_builder.build(query, results)

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        embeddings = self.embedding_model.embed(self.knowledge_base)
        self.vector_store.add_texts(self.knowledge_base, embeddings)
        self._initialized = True

