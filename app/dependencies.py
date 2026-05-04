from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db_session, get_session_factory
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.ingestion.csv_parser import CsvFeedbackParser
from app.domain.ingestion.image_downloader import ImageDownloader
from app.domain.ingestion.image_preprocessor import ImagePreprocessor
from app.domain.ingestion.ingestion_service import IngestionService
from app.domain.ingestion.multimodal_ingestion_service import MultimodalIngestionService
from app.domain.ingestion.pdf_text_extractor import PdfTextExtractor
from app.domain.ingestion.tesseract_ocr import TesseractOcrEngine
from app.domain.ingestion.text_normalizer import TextNormalizer
from app.domain.knowledge.external_data import external_data
from app.domain.processing.queue import CeleryProcessingQueue, ProcessingQueue
from app.domain.processing.service import ProcessingService
from app.domain.retrieval.faiss_vector_store import FaissVectorStore
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.retrieval_service import RetrievalService
from app.domain.retrieval.sentence_transformer_embeddings import SentenceTransformerEmbeddingModel
from app.domain.routing.keyword_team_router import KeywordTeamRouter
from app.domain.sentiment.hf_sentiment_analyzer import HuggingFaceSentimentAnalyzer
from app.domain.storage.local_storage_provider import LocalFileStorageProvider
from app.domain.storage.storage_provider import StorageProvider


@lru_cache
def get_image_downloader() -> ImageDownloader:
    settings = get_settings()
    return ImageDownloader(settings.request_timeout_seconds, settings.max_image_bytes)


@lru_cache
def get_ingestion_service() -> IngestionService:
    settings = get_settings()
    return IngestionService(
        preprocessor=ImagePreprocessor(),
        ocr_engine=TesseractOcrEngine(settings.ocr_languages, settings.tesseract_timeout_seconds),
        downloader=get_image_downloader(),
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


def get_feedback_repository(session: Session = Depends(get_db_session)) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(repository: FeedbackRepository = Depends(get_feedback_repository)) -> FeedbackService:
    return FeedbackService(repository, TextNormalizer())


def get_processing_queue() -> ProcessingQueue:
    return CeleryProcessingQueue()


def get_processing_service(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    analysis_service: FeedbackAnalysisService = Depends(get_feedback_analysis_service),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> ProcessingService:
    return ProcessingService(
        feedback_service=feedback_service,
        analysis_service=analysis_service,
        queue=queue,
        settings=get_settings(),
    )


@contextmanager
def feedback_service_scope() -> Iterator[FeedbackService]:
    session = get_session_factory()()
    try:
        yield FeedbackService(FeedbackRepository(session))
    finally:
        session.close()


def get_feedback_service_scope_provider() -> Callable[[], AbstractContextManager[FeedbackService]]:
    return feedback_service_scope


@lru_cache
def get_storage_provider() -> StorageProvider:
    return LocalFileStorageProvider(get_settings().local_storage_dir)


def get_pdf_text_extractor() -> PdfTextExtractor:
    return PdfTextExtractor()


def get_csv_feedback_parser() -> CsvFeedbackParser:
    return CsvFeedbackParser()


def get_multimodal_ingestion_service(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    storage_provider: StorageProvider = Depends(get_storage_provider),
    image_ingestion_service: IngestionService = Depends(get_ingestion_service),
    image_downloader: ImageDownloader = Depends(get_image_downloader),
    pdf_text_extractor: PdfTextExtractor = Depends(get_pdf_text_extractor),
    csv_parser: CsvFeedbackParser = Depends(get_csv_feedback_parser),
) -> MultimodalIngestionService:
    settings = get_settings()
    return MultimodalIngestionService(
        feedback_service=feedback_service,
        storage_provider=storage_provider,
        image_ingestion_service=image_ingestion_service,
        image_downloader=image_downloader,
        pdf_text_extractor=pdf_text_extractor,
        csv_parser=csv_parser,
        max_image_bytes=settings.max_image_bytes,
        max_pdf_bytes=settings.max_pdf_bytes,
        max_csv_bytes=settings.max_csv_bytes,
    )
