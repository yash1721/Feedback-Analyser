from functools import lru_cache

from app.config import get_settings
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService
from app.domain.ingestion.image_downloader import ImageDownloader
from app.domain.ingestion.image_preprocessor import ImagePreprocessor
from app.domain.ingestion.ingestion_service import IngestionService
from app.domain.ingestion.tesseract_ocr import TesseractOcrEngine
from app.domain.knowledge.external_data import external_data
from app.domain.retrieval.faiss_vector_store import FaissVectorStore
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.retrieval_service import RetrievalService
from app.domain.retrieval.sentence_transformer_embeddings import SentenceTransformerEmbeddingModel
from app.domain.routing.keyword_team_router import KeywordTeamRouter
from app.domain.sentiment.hf_sentiment_analyzer import HuggingFaceSentimentAnalyzer


@lru_cache
def get_ingestion_service() -> IngestionService:
    settings = get_settings()
    return IngestionService(
        preprocessor=ImagePreprocessor(),
        ocr_engine=TesseractOcrEngine(settings.ocr_languages, settings.tesseract_timeout_seconds),
        downloader=ImageDownloader(settings.request_timeout_seconds, settings.max_image_bytes),
    )


@lru_cache
def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        embedding_model=SentenceTransformerEmbeddingModel(settings.embedding_model_name),
        vector_store=FaissVectorStore(),
        context_builder=RagContextBuilder(),
        knowledge_base=external_data,
    )


@lru_cache
def get_feedback_analysis_service() -> FeedbackAnalysisService:
    settings = get_settings()
    return FeedbackAnalysisService(
        sentiment_analyzer=HuggingFaceSentimentAnalyzer(settings.sentiment_model_name),
        team_router=KeywordTeamRouter(),
        retrieval_service=get_retrieval_service(),
    )

