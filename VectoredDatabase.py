"""Deprecated compatibility helpers for the old FAISS demo script.

The production code now lives under app.domain.retrieval, app.domain.sentiment,
and app.domain.routing. This module no longer runs sample queries on import.
"""

from app.config import get_settings
from app.domain.knowledge.external_data import external_data
from app.domain.retrieval.faiss_vector_store import FaissVectorStore
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.retrieval_service import RetrievalService
from app.domain.retrieval.sentence_transformer_embeddings import SentenceTransformerEmbeddingModel
from app.domain.routing.keyword_team_router import KeywordTeamRouter
from app.domain.sentiment.hf_sentiment_analyzer import HuggingFaceSentimentAnalyzer


def build_retrieval_service() -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        embedding_model=SentenceTransformerEmbeddingModel(settings.embedding_model_name),
        vector_store=FaissVectorStore(),
        context_builder=RagContextBuilder(),
        knowledge_base=external_data,
    )


def search_similar(query: str, top_k: int = 3):
    return build_retrieval_service().search(query, top_k)


def prepare_for_rag(query: str, results):
    return RagContextBuilder().build(query, results)


def analyze_sentiment(query: str):
    settings = get_settings()
    result = HuggingFaceSentimentAnalyzer(settings.sentiment_model_name).analyze(query)
    return result.label, result.score


def identify_team(context: str):
    return KeywordTeamRouter().route(context).team


if __name__ == "__main__":
    sample_query = "I really like the animations on the homepage."
    results, rag_context = build_retrieval_service().build_context(sample_query, 3)
    sentiment, score = analyze_sentiment(sample_query)
    print("Similarity Search Results:")
    for result in results:
        print(f"- {result.text} ({result.score:.4f})")
    print("\nRAG Input:")
    print(rag_context)
    print("\nFinal Analysis:")
    print(f"Sentiment: {sentiment} ({score:.2f})")
    print(f"Relevant Team: {identify_team(rag_context)}")

