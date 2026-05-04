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
from app.domain.knowledge.repository import KnowledgeRepository
from app.domain.knowledge.service import KnowledgeService
from app.domain.processing.queue import CeleryProcessingQueue, ProcessingQueue
from app.domain.processing.service import ProcessingService
from app.domain.retrieval.bge_m3_embeddings import BGEM3EmbeddingModel
from app.domain.retrieval.faiss_vector_store import FaissVectorStore
from app.domain.retrieval.embedding_model import EmbeddingModel
from app.domain.retrieval.qdrant_vector_store import QdrantVectorStore
from app.domain.retrieval.rag_context_builder import RagContextBuilder
from app.domain.retrieval.retrieval_service import RetrievalService
from app.domain.retrieval.sentence_transformer_embeddings import SentenceTransformerEmbeddingModel
from app.domain.retrieval.vector_store import VectorStore
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
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    if settings.embedding_provider == "bge_m3":
        return BGEM3EmbeddingModel(settings.embedding_model_name)
    return SentenceTransformerEmbeddingModel(settings.embedding_model_name)


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_provider == "qdrant":
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.vector_size,
            distance=settings.vector_distance,
        )
    return FaissVectorStore()


def get_knowledge_repository(session: Session = Depends(get_db_session)) -> KnowledgeRepository:
    return KnowledgeRepository(session)


def get_knowledge_service(
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
    embedding_model: EmbeddingModel = Depends(get_embedding_model),
    vector_store: VectorStore = Depends(get_vector_store),
) -> KnowledgeService:
    return KnowledgeService(
        repository=repository,
        embedding_model=embedding_model,
        vector_store=vector_store,
        settings=get_settings(),
    )


def build_retrieval_service(knowledge_service: KnowledgeService | None = None) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        embedding_model=get_embedding_model(),
        vector_store=get_vector_store(),
        context_builder=RagContextBuilder(),
        knowledge_base=external_data,
        settings=settings,
        knowledge_service=knowledge_service,
    )


def get_retrieval_service(
    embedding_model: EmbeddingModel = Depends(get_embedding_model),
    vector_store: VectorStore = Depends(get_vector_store),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        embedding_model=embedding_model,
        vector_store=vector_store,
        context_builder=RagContextBuilder(),
        knowledge_base=external_data,
        settings=settings,
        knowledge_service=knowledge_service,
    )


def get_feedback_analysis_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> FeedbackAnalysisService:
    settings = get_settings()
    return FeedbackAnalysisService(
        sentiment_analyzer=HuggingFaceSentimentAnalyzer(settings.sentiment_model_name),
        team_router=KeywordTeamRouter(),
        retrieval_service=retrieval_service,
    )


def get_feedback_analysis_service_for_worker() -> FeedbackAnalysisService:
    settings = get_settings()
    return FeedbackAnalysisService(
        sentiment_analyzer=HuggingFaceSentimentAnalyzer(settings.sentiment_model_name),
        team_router=KeywordTeamRouter(),
        retrieval_service=build_retrieval_service(),
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
