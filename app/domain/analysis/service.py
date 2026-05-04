from app.config import Settings
from app.core.exceptions import BadRequestError, FeedbackIQError, NotFoundError
from app.domain.analysis.confidence import apply_confidence_policy
from app.domain.analysis.output_parser import AnalysisOutputParseError, parse_structured_analysis
from app.domain.analysis.prompts import build_feedback_analysis_prompt
from app.domain.analysis.repository import AnalysisRepository
from app.domain.analysis.schemas import AnalysisResponse, StructuredAnalysisOutput, ValidationStatus
from app.domain.feedback.models import FeedbackRecord
from app.domain.feedback.service import FeedbackService
from app.domain.llm.provider import LLMProvider
from app.domain.retrieval.retrieval_service import RetrievalService


class AnalysisService:
    def __init__(
        self,
        *,
        repository: AnalysisRepository,
        feedback_service: FeedbackService,
        retrieval_service: RetrievalService,
        provider: LLMProvider,
        fallback_provider: LLMProvider | None,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.feedback_service = feedback_service
        self.retrieval_service = retrieval_service
        self.provider = provider
        self.fallback_provider = fallback_provider
        self.settings = settings

    def run_feedback_analysis(self, feedback_id: int) -> AnalysisResponse:
        record = self.feedback_service.get_feedback_record(feedback_id)
        text = self._analysis_text(record)
        retrieval = self.retrieval_service.search_with_options(
            text,
            top_k=self.settings.retrieval_top_k,
            persist_trace=True,
            feedback_record_id=feedback_id,
        )
        prompt = build_feedback_analysis_prompt(
            feedback_text=text,
            evidence=retrieval.results,
            prompt_version=self.settings.llm_prompt_version,
        )
        provider = self.provider
        try:
            provider_response = provider.analyze_feedback(prompt)
        except Exception as exc:
            if self.fallback_provider is None:
                run = self._persist_failed_run(
                    feedback_id=feedback_id,
                    retrieval_trace_id=retrieval.trace_id,
                    provider=provider.provider_name,
                    model_name=provider.model_name,
                    error_code="provider_error",
                    error_message="LLM provider failed.",
                    input_preview=text,
                )
                raise FeedbackIQError("LLM provider failed.", {"analysis_run_id": run.id}) from exc
            provider = self.fallback_provider
            provider_response = provider.analyze_feedback(prompt)

        try:
            output = parse_structured_analysis(provider_response.raw_output)
            output = apply_confidence_policy(
                output,
                evidence=retrieval.results,
                threshold=self.settings.llm_confidence_threshold,
            )
        except AnalysisOutputParseError as exc:
            run = self.repository.create_run(
                feedback_record_id=feedback_id,
                retrieval_trace_id=retrieval.trace_id,
                provider=provider_response.provider,
                model_name=provider_response.model_name,
                prompt_version=prompt.version,
                input_preview=text[:500],
                output_json=provider_response.raw_output if isinstance(provider_response.raw_output, dict) else None,
                validation_status=ValidationStatus.INVALID.value,
                error_code="validation_error",
                error_message=exc.message,
            )
            self.repository.session.commit()
            return AnalysisResponse(
                feedback_id=feedback_id,
                analysis_run_id=run.id,
                retrieval_trace_id=retrieval.trace_id,
                validation_status=ValidationStatus.INVALID,
                output=None,
                provider=provider_response.provider,
                model_name=provider_response.model_name,
                prompt_version=prompt.version,
                error_code="validation_error",
                error_message=exc.message,
            )

        run = self.repository.create_run(
            feedback_record_id=feedback_id,
            retrieval_trace_id=retrieval.trace_id,
            provider=provider_response.provider,
            model_name=provider_response.model_name,
            prompt_version=prompt.version,
            input_preview=text[:500],
            output_json=output.model_dump(mode="json"),
            validation_status=ValidationStatus.VALID.value,
        )
        self.repository.session.commit()
        self.feedback_service.attach_structured_analysis_result(feedback_id, analysis_run_id=run.id, output=output)
        return AnalysisResponse(
            feedback_id=feedback_id,
            analysis_run_id=run.id,
            retrieval_trace_id=retrieval.trace_id,
            validation_status=ValidationStatus.VALID,
            output=output,
            provider=provider_response.provider,
            model_name=provider_response.model_name,
            prompt_version=prompt.version,
        )

    def get_run(self, run_id: int):
        run = self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError("Analysis run was not found.", {"run_id": run_id})
        return run

    def get_latest_run(self, feedback_id: int):
        self.feedback_service.get_feedback_record(feedback_id)
        return self.repository.get_latest_for_feedback(feedback_id)

    def _persist_failed_run(
        self,
        *,
        feedback_id: int,
        retrieval_trace_id: int | None,
        provider: str,
        model_name: str,
        error_code: str,
        error_message: str,
        input_preview: str,
    ):
        run = self.repository.create_run(
            feedback_record_id=feedback_id,
            retrieval_trace_id=retrieval_trace_id,
            provider=provider,
            model_name=model_name,
            prompt_version=self.settings.llm_prompt_version,
            input_preview=input_preview[:500],
            output_json=None,
            validation_status=ValidationStatus.FAILED.value,
            error_code=error_code,
            error_message=error_message,
        )
        self.repository.session.commit()
        return run

    @staticmethod
    def _analysis_text(record: FeedbackRecord) -> str:
        text = record.normalized_text or record.extracted_text or record.raw_text
        if not text:
            raise BadRequestError("Feedback record does not contain text that can be analyzed.", {"feedback_id": record.id})
        return text
