from fastapi import APIRouter, Depends

from app.core.pagination import PaginationParams
from app.core.responses import success_response
from app.dependencies import get_knowledge_service
from app.domain.knowledge.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetail,
    KnowledgeDocumentIndexResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentRead,
)
from app.domain.knowledge.service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/documents")
def create_knowledge_document(
    payload: KnowledgeDocumentCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict:
    document = service.create_document(
        title=payload.title,
        text=payload.text,
        source_type=payload.source_type,
        source_name=payload.source_name,
        metadata=payload.metadata,
    )
    return success_response(data=KnowledgeDocumentRead.model_validate(document).model_dump(mode="json"))


@router.get("/documents")
def list_knowledge_documents(
    pagination: PaginationParams = Depends(),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict:
    documents = service.list_documents(limit=pagination.limit, offset=pagination.offset)
    response = KnowledgeDocumentListResponse(
        items=[KnowledgeDocumentRead.model_validate(document) for document in documents],
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/documents/{document_id}")
def get_knowledge_document(
    document_id: int,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict:
    document = service.get_document(document_id)
    return success_response(data=KnowledgeDocumentDetail.model_validate(document).model_dump(mode="json"))


@router.post("/documents/{document_id}/index")
def index_knowledge_document(
    document_id: int,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict:
    document, indexed_chunks = service.index_document(document_id)
    response = KnowledgeDocumentIndexResponse(
        document_id=document.id,
        indexed_chunks=indexed_chunks,
        vector_provider=service.settings.vector_provider,
        embedding_provider=service.settings.embedding_provider,
    )
    return success_response(data=response.model_dump(mode="json"))
