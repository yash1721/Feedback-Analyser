from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db_session, get_session_factory
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.report import AnalyticsReportGenerator
from app.domain.analytics.service import AnalyticsService
from app.domain.analysis.repository import AnalysisRepository
from app.domain.analysis.service import AnalysisService
from app.domain.evaluation.datasets import EvaluationDatasetLoader
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.evaluation.report import EvaluationReportGenerator
from app.domain.evaluation.service import EvaluationService
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.guardrails.output_guardrails import OutputGuardrailService
from app.domain.guardrails.pii_redaction import PIIRedactionService
from app.domain.guardrails.prompt_injection import PromptInjectionDetector
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
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.llm.provider import LLMProvider
from app.domain.llm.rule_based_provider import RuleBasedAnalysisProvider
from app.domain.notifications.log_provider import LogNotificationProvider
from app.domain.notifications.mock_provider import MockNotificationProvider
from app.domain.notifications.provider import NotificationProvider
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
from app.domain.security.repository import SecurityAuditRepository
from app.domain.security.service import SecurityAuditService
from app.domain.storage.local_storage_provider import LocalFileStorageProvider
from app.domain.storage.storage_provider import StorageProvider
from app.domain.workflow.repository import WorkflowRepository
from app.domain.workflow.service import WorkflowService


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
    prompt_injection_detector: PromptInjectionDetector = Depends(lambda: PromptInjectionDetector()),
) -> KnowledgeService:
    return KnowledgeService(
        repository=repository,
        embedding_model=embedding_model,
        vector_store=vector_store,
        settings=get_settings(),
        prompt_injection_detector=prompt_injection_detector,
    )


def get_analysis_repository(session: Session = Depends(get_db_session)) -> AnalysisRepository:
    return AnalysisRepository(session)


def get_evaluation_repository(session: Session = Depends(get_db_session)) -> EvaluationRepository:
    return EvaluationRepository(session)


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMProvider(settings.llm_model_name)
    return RuleBasedAnalysisProvider(settings.llm_model_name)


def get_llm_fallback_provider() -> LLMProvider | None:
    settings = get_settings()
    if settings.llm_fallback_provider == "rule_based":
        return RuleBasedAnalysisProvider("rule-based-feedback-analyzer-v1")
    return None


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


def build_analysis_service(feedback_service: FeedbackService) -> AnalysisService:
    session = feedback_service.repository.session
    knowledge_service = KnowledgeService(
        repository=KnowledgeRepository(session),
        embedding_model=get_embedding_model(),
        vector_store=get_vector_store(),
        settings=get_settings(),
        prompt_injection_detector=PromptInjectionDetector(),
    )
    return AnalysisService(
        repository=AnalysisRepository(session),
        feedback_service=feedback_service,
        retrieval_service=build_retrieval_service(knowledge_service),
        provider=get_llm_provider(),
        fallback_provider=get_llm_fallback_provider(),
        settings=get_settings(),
        output_guardrail_service=OutputGuardrailService(),
    )


def build_workflow_service(feedback_service: FeedbackService) -> WorkflowService:
    return WorkflowService(
        repository=WorkflowRepository(feedback_service.repository.session),
        feedback_service=feedback_service,
        notification_provider=get_notification_provider(),
        settings=get_settings(),
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


def get_analytics_repository(session: Session = Depends(get_db_session)) -> AnalyticsRepository:
    return AnalyticsRepository(session)


def get_analytics_service(
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> AnalyticsService:
    settings = get_settings()
    return AnalyticsService(
        repository=repository,
        report_generator=AnalyticsReportGenerator(settings.analytics_report_dir),
    )


def get_feedback_repository(session: Session = Depends(get_db_session)) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(repository: FeedbackRepository = Depends(get_feedback_repository)) -> FeedbackService:
    return FeedbackService(repository, TextNormalizer())


def get_workflow_repository(session: Session = Depends(get_db_session)) -> WorkflowRepository:
    return WorkflowRepository(session)


def get_notification_provider() -> NotificationProvider:
    settings = get_settings()
    if settings.notification_provider == "mock":
        return MockNotificationProvider()
    return LogNotificationProvider()


def get_workflow_service(
    repository: WorkflowRepository = Depends(get_workflow_repository),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    notification_provider: NotificationProvider = Depends(get_notification_provider),
) -> WorkflowService:
    return WorkflowService(
        repository=repository,
        feedback_service=feedback_service,
        notification_provider=notification_provider,
        settings=get_settings(),
    )


def get_analysis_service(
    repository: AnalysisRepository = Depends(get_analysis_repository),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    provider: LLMProvider = Depends(get_llm_provider),
    fallback_provider: LLMProvider | None = Depends(get_llm_fallback_provider),
    output_guardrail_service: OutputGuardrailService = Depends(lambda: OutputGuardrailService()),
) -> AnalysisService:
    return AnalysisService(
        repository=repository,
        feedback_service=feedback_service,
        retrieval_service=retrieval_service,
        provider=provider,
        fallback_provider=fallback_provider,
        settings=get_settings(),
        output_guardrail_service=output_guardrail_service,
    )


def get_security_audit_repository(session: Session = Depends(get_db_session)) -> SecurityAuditRepository:
    return SecurityAuditRepository(session)


def get_security_audit_service(
    repository: SecurityAuditRepository = Depends(get_security_audit_repository),
) -> SecurityAuditService:
    return SecurityAuditService(repository)


def get_evaluation_service(
    repository: EvaluationRepository = Depends(get_evaluation_repository),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    provider: LLMProvider = Depends(get_llm_provider),
) -> EvaluationService:
    settings = get_settings()
    return EvaluationService(
        repository=repository,
        retrieval_service=retrieval_service,
        provider=provider,
        settings=settings,
        dataset_loader=EvaluationDatasetLoader(),
        report_generator=EvaluationReportGenerator(settings.evaluation_report_dir),
    )


def get_processing_queue() -> ProcessingQueue:
    return CeleryProcessingQueue()


def get_processing_service(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    analysis_service: FeedbackAnalysisService = Depends(get_feedback_analysis_service),
    llm_analysis_service: AnalysisService = Depends(get_analysis_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> ProcessingService:
    return ProcessingService(
        feedback_service=feedback_service,
        analysis_service=analysis_service,
        llm_analysis_service=llm_analysis_service,
        workflow_service=workflow_service,
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
    security_audit_service: SecurityAuditService = Depends(get_security_audit_service),
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
        settings=settings,
        pii_service=PIIRedactionService(),
        prompt_injection_detector=PromptInjectionDetector(),
        security_audit_service=security_audit_service,
    )
