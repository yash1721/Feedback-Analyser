"""Deprecated PDF RAG experiment.

Phase 0 keeps this file as a reference placeholder only. The production
retrieval path is app.domain.retrieval and uses local embeddings plus FAISS.
PDF ingestion with LangChain/Chroma can be reintroduced in a later phase.
"""


def main() -> None:
    print("PDF RAG experiment is deprecated in Phase 0. See app.domain.retrieval.")


if __name__ == "__main__":
    main()

