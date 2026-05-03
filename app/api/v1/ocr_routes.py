from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, HttpUrl

from app.config import get_settings
from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.responses import success_response
from app.dependencies import get_ingestion_service
from app.domain.ingestion.ingestion_service import IngestionService

router = APIRouter(prefix="/ocr", tags=["ocr"])


class ExtractFromUrlRequest(BaseModel):
    url: HttpUrl


@router.post("/extract")
async def extract_from_upload(
    file: UploadFile = File(...),
    service: IngestionService = Depends(get_ingestion_service),
) -> dict:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise UnsupportedMediaTypeError("Uploaded file must be an image.", {"content_type": content_type})

    image_bytes = await file.read()
    if len(image_bytes) > get_settings().max_image_bytes:
        raise PayloadTooLargeError("Uploaded image exceeds the configured maximum size.")

    text = service.extract_from_bytes(image_bytes)
    return success_response(data={"text": text})


@router.post("/extract-from-url")
def extract_from_url(
    payload: ExtractFromUrlRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> dict:
    text = service.extract_from_url(str(payload.url))
    return success_response(data={"text": text, "url": str(payload.url)})
