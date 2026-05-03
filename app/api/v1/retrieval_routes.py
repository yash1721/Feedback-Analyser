from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.responses import success_response
from app.dependencies import get_retrieval_service
from app.domain.retrieval.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


@router.post("/search")
def search(
    payload: RetrievalSearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> dict:
    settings = get_settings()
    top_k = payload.top_k or settings.retrieval_top_k
    results, rag_context = service.build_context(payload.query, top_k)
    return success_response(
        data={
            "query": payload.query,
            "results": [{"text": result.text, "score": result.score} for result in results],
            "rag_context": rag_context,
        }
    )

