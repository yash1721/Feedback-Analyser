from fastapi import APIRouter, Depends, File, UploadFile

from app.core.responses import success_response
from app.dependencies import get_multimodal_ingestion_service
from app.domain.feedback.models import FeedbackSourceType
from app.domain.ingestion.multimodal_ingestion_service import MultimodalIngestionService
from app.domain.ingestion.schemas import (
    CsvIngestionResponse,
    CsvRowError,
    ImageUrlIngestionRequest,
    IngestionResult,
    TextIngestionRequest,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/text")
def ingest_text(
    payload: TextIngestionRequest,
    service: MultimodalIngestionService = Depends(get_multimodal_ingestion_service),
) -> dict:
    record = service.ingest_text(payload.text)
    return success_response(data=_to_ingestion_result(record).model_dump(mode="json"))


@router.post("/image")
async def ingest_image_upload(
    file: UploadFile = File(...),
    service: MultimodalIngestionService = Depends(get_multimodal_ingestion_service),
) -> dict:
    record = service.ingest_image_upload(
        content=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )
    return success_response(data=_to_ingestion_result(record).model_dump(mode="json"))


@router.post("/image-url")
def ingest_image_url(
    payload: ImageUrlIngestionRequest,
    service: MultimodalIngestionService = Depends(get_multimodal_ingestion_service),
) -> dict:
    record = service.ingest_image_url(str(payload.url))
    return success_response(data=_to_ingestion_result(record).model_dump(mode="json"))


@router.post("/pdf")
async def ingest_pdf_upload(
    file: UploadFile = File(...),
    service: MultimodalIngestionService = Depends(get_multimodal_ingestion_service),
) -> dict:
    record = service.ingest_pdf_upload(
        content=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )
    return success_response(data=_to_ingestion_result(record).model_dump(mode="json"))


@router.post("/csv")
async def ingest_csv_upload(
    file: UploadFile = File(...),
    service: MultimodalIngestionService = Depends(get_multimodal_ingestion_service),
) -> dict:
    storage_key, records, row_errors = service.ingest_csv_upload(
        content=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )
    response = CsvIngestionResponse(
        source_type=FeedbackSourceType.CSV,
        original_input_reference=storage_key,
        created_count=len(records),
        failed_count=len(row_errors),
        feedback_ids=[record.id for record in records],
        row_errors=[CsvRowError(**row_error) for row_error in row_errors],
    )
    return success_response(data=response.model_dump(mode="json"))


def _to_ingestion_result(record) -> IngestionResult:
    return IngestionResult(
        feedback_id=record.id,
        source_type=record.source_type,
        processing_status=record.processing_status,
        original_input_reference=record.original_input_reference,
        raw_text=record.raw_text,
        extracted_text=record.extracted_text,
        normalized_text=record.normalized_text,
        error_code=record.error_code,
        error_message=record.error_message,
    )
