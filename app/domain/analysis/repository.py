from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.analysis.models import LLMAnalysisRun


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        *,
        feedback_record_id: int,
        retrieval_trace_id: int | None,
        provider: str,
        model_name: str,
        prompt_version: str,
        input_preview: str | None,
        output_json: dict | None,
        validation_status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> LLMAnalysisRun:
        run = LLMAnalysisRun(
            feedback_record_id=feedback_record_id,
            retrieval_trace_id=retrieval_trace_id,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
            input_preview=input_preview,
            output_json=output_json,
            validation_status=validation_status,
            error_code=error_code,
            error_message=error_message,
        )
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def get_run(self, run_id: int) -> LLMAnalysisRun | None:
        return self.session.get(LLMAnalysisRun, run_id)

    def get_latest_for_feedback(self, feedback_record_id: int) -> LLMAnalysisRun | None:
        return self.session.scalar(
            select(LLMAnalysisRun)
            .where(LLMAnalysisRun.feedback_record_id == feedback_record_id)
            .order_by(LLMAnalysisRun.created_at.desc(), LLMAnalysisRun.id.desc())
            .limit(1)
        )
