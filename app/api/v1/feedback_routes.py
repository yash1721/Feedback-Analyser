from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.responses import success_response
from app.dependencies import get_feedback_analysis_service
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


@router.post("/analyze")
def analyze_feedback(
    payload: FeedbackAnalyzeRequest,
    service: FeedbackAnalysisService = Depends(get_feedback_analysis_service),
) -> dict:
    settings = get_settings()
    result = service.analyze(payload.text, payload.top_k or settings.retrieval_top_k)
    return success_response(
        data={
            "text": result.text,
            "sentiment": {"label": result.sentiment.label, "score": result.sentiment.score},
            "routing": {
                "team": result.routing.team,
                "matched_keyword": result.routing.matched_keyword,
            },
            "retrieval": [
                {"text": item.text, "score": item.score}
                for item in result.retrieval_results
            ],
            "rag_context": result.rag_context,
        }
    )

