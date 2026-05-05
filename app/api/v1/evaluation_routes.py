from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.core.auth import require_permission
from app.core.pagination import PaginationParams
from app.core.responses import success_response
from app.dependencies import get_evaluation_service
from app.domain.evaluation.schemas import (
    EvaluationRunCreate,
    EvaluationRunDetail,
    EvaluationRunListResponse,
    EvaluationRunSummary,
)
from app.domain.evaluation.service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(require_permission("evaluation:read"))])


@router.post("/runs")
def run_evaluation(
    payload: EvaluationRunCreate,
    _=Depends(require_permission("evaluation:run")),
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict:
    result = service.run_evaluation(payload)
    return success_response(data=result.model_dump(mode="json"))


@router.get("/runs")
def list_evaluation_runs(
    pagination: PaginationParams = Depends(),
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict:
    runs, total = service.list_runs(limit=pagination.limit, offset=pagination.offset)
    response = EvaluationRunListResponse(
        items=[EvaluationRunSummary.model_validate(run) for run in runs],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/runs/{run_id}")
def get_evaluation_run(
    run_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict:
    run = service.get_run(run_id)
    response = EvaluationRunDetail.model_validate(run)
    return success_response(data=response.model_dump(mode="json"))


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def get_evaluation_report(
    run_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> str:
    return service.read_report(run_id)
