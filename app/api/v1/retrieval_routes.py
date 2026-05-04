from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Any

from app.config import get_settings
from app.core.responses import success_response
from app.dependencies import get_retrieval_service
from app.domain.retrieval.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    filters: dict[str, Any] | None = None
    persist_trace: bool = False
    feedback_record_id: int | None = None


@router.post("/search")
def search(
    payload: RetrievalSearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> dict:
    settings = get_settings()
    top_k = payload.top_k or settings.retrieval_top_k
    search_result = service.search_with_options(
        payload.query,
        top_k=top_k,
        filters=payload.filters,
        persist_trace=payload.persist_trace,
        feedback_record_id=payload.feedback_record_id,
    )
    return success_response(
        data={
            "query": payload.query,
            "results": [
                {
                    "text": result.text,
                    "score": result.score,
                    "rank": result.rank,
                    "point_id": result.point_id,
                    "chunk_id": result.chunk_id,
                    "metadata": result.metadata,
                }
                for result in search_result.results
            ],
            "trace_id": search_result.trace_id,
            "rag_context": search_result.rag_context,
        }
    )
