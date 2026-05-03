from dataclasses import dataclass

from app.domain.retrieval.retrieval_service import RetrievalService
from app.domain.retrieval.vector_store import SearchResult
from app.domain.routing.team_router import RoutingResult, TeamRouter
from app.domain.sentiment.sentiment_analyzer import SentimentAnalyzer, SentimentResult


@dataclass(frozen=True)
class FeedbackAnalysisResult:
    text: str
    sentiment: SentimentResult
    routing: RoutingResult
    retrieval_results: list[SearchResult]
    rag_context: str


class FeedbackAnalysisService:
    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzer,
        team_router: TeamRouter,
        retrieval_service: RetrievalService,
    ) -> None:
        self.sentiment_analyzer = sentiment_analyzer
        self.team_router = team_router
        self.retrieval_service = retrieval_service

    def analyze(self, text: str, top_k: int) -> FeedbackAnalysisResult:
        retrieval_results, rag_context = self.retrieval_service.build_context(text, top_k)
        sentiment = self.sentiment_analyzer.analyze(text)
        routing = self.team_router.route(f"{text}\n{rag_context}")
        return FeedbackAnalysisResult(
            text=text,
            sentiment=sentiment,
            routing=routing,
            retrieval_results=retrieval_results,
            rag_context=rag_context,
        )

