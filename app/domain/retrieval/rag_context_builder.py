from app.domain.retrieval.vector_store import SearchResult


class RagContextBuilder:
    def build(self, query: str, results: list[SearchResult]) -> str:
        context = "\n".join(result.text for result in results)
        return f"Query: {query}\n\nContext:\n{context}"

