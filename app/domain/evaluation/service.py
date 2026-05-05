from pathlib import Path
from time import perf_counter

from app.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.analysis.confidence import apply_confidence_policy
from app.domain.analysis.output_parser import AnalysisOutputParseError, parse_structured_analysis
from app.domain.analysis.prompts import build_feedback_analysis_prompt
from app.domain.evaluation.datasets import EvaluationDatasetLoader
from app.domain.evaluation.metrics import (
    aggregate_item_metrics,
    groundedness_check,
    label_metrics,
    retrieval_metrics,
    workflow_metrics,
)
from app.domain.evaluation.models import EvaluationDataset, EvaluationRun
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.evaluation.report import EvaluationReportGenerator
from app.domain.evaluation.schemas import EvaluationRunCreate, EvaluationRunResult, EvaluationRunSummary
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.llm.provider import LLMProvider
from app.domain.llm.rule_based_provider import RuleBasedAnalysisProvider
from app.domain.retrieval.retrieval_service import RetrievalService


class EvaluationService:
    def __init__(
        self,
        *,
        repository: EvaluationRepository,
        retrieval_service: RetrievalService,
        provider: LLMProvider,
        settings: Settings,
        dataset_loader: EvaluationDatasetLoader | None = None,
        report_generator: EvaluationReportGenerator | None = None,
    ) -> None:
        self.repository = repository
        self.retrieval_service = retrieval_service
        self.provider = provider
        self.settings = settings
        self.dataset_loader = dataset_loader or EvaluationDatasetLoader()
        self.report_generator = report_generator or EvaluationReportGenerator(settings.evaluation_report_dir)

    def run_evaluation(self, request: EvaluationRunCreate) -> EvaluationRunResult:
        dataset = self.dataset_loader.load(request.dataset_path)
        dataset_name = request.dataset_name or dataset.name
        prompt_version = request.prompt_version or self.settings.llm_prompt_version
        top_k = request.top_k or self.settings.retrieval_top_k
        provider = self._provider_for_request(request)
        persisted_dataset = self._persist_dataset(
            dataset_name=dataset_name,
            dataset_version=dataset.version,
            description=dataset.description,
            source_path=request.dataset_path,
            examples=dataset.examples,
            enabled=request.persist_dataset,
        )
        run = self.repository.create_run(
            dataset_id=persisted_dataset.id if persisted_dataset else None,
            dataset_name=dataset_name,
            dataset_version=dataset.version,
            provider=provider.provider_name,
            model_name=provider.model_name,
            prompt_version=prompt_version,
            vector_provider=self.settings.vector_provider,
            embedding_model=self.settings.embedding_model_name,
            top_k=top_k,
            total_examples=len(dataset.examples),
            metrics_json=None,
            report_path=None,
        )
        self.repository.session.commit()

        item_metrics: list[dict] = []
        examples_by_external_id = self._persisted_examples_by_external_id(persisted_dataset)
        for example in dataset.examples:
            metrics = self._evaluate_example(
                run=run,
                persisted_example=examples_by_external_id.get(example.id),
                example=example,
                prompt_version=prompt_version,
                top_k=top_k,
                provider=provider,
            )
            item_metrics.append(metrics)

        aggregate = aggregate_item_metrics(item_metrics)
        self.repository.update_run(run, metrics_json=aggregate)
        self.repository.session.commit()
        report_path = None
        if request.write_report:
            report_path = self.report_generator.write_reports(run, item_metrics)
            self.repository.update_run(run, report_path=report_path)
            self.repository.session.commit()
        return EvaluationRunResult(
            run=EvaluationRunSummary.model_validate(run),
            metrics=aggregate,
            report_path=report_path,
        )

    def get_run(self, run_id: int) -> EvaluationRun:
        run = self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError("Evaluation run was not found.", {"run_id": run_id})
        return run

    def list_runs(self, *, limit: int, offset: int):
        return self.repository.list_runs(limit=limit, offset=offset)

    def read_report(self, run_id: int) -> str:
        run = self.get_run(run_id)
        if not run.report_path:
            raise NotFoundError("Evaluation report was not found for this run.", {"run_id": run_id})
        path = Path(run.report_path)
        if not path.exists():
            raise NotFoundError("Evaluation report file was not found.", {"run_id": run_id, "report_path": run.report_path})
        return path.read_text(encoding="utf-8")

    def _provider_for_request(self, request: EvaluationRunCreate) -> LLMProvider:
        model_name = request.model_name
        if request.provider == "fake":
            return FakeLLMProvider(model_name or "fake-feedback-analyzer")
        if request.provider == "rule_based":
            return RuleBasedAnalysisProvider(model_name or "rule-based-feedback-analyzer-v1")
        return self.provider

    def _persisted_examples_by_external_id(self, dataset: EvaluationDataset | None) -> dict:
        if dataset is None:
            return {}
        refreshed = self.repository.get_dataset_by_name_version(name=dataset.name, version=dataset.version)
        if refreshed is None:
            return {}
        return {example.external_id: example for example in refreshed.examples}

    def _persist_dataset(
        self,
        *,
        dataset_name: str,
        dataset_version: str,
        description: str | None,
        source_path: str | None,
        examples,
        enabled: bool,
    ) -> EvaluationDataset | None:
        if not enabled:
            return None
        dataset = self.repository.get_dataset_by_name_version(name=dataset_name, version=dataset_version)
        if dataset is None:
            dataset = self.repository.create_dataset(
                name=dataset_name,
                version=dataset_version,
                description=description,
                source_path=source_path,
                metadata_json={"source": "fixture" if source_path is None else "file"},
            )
        self.repository.replace_examples(
            dataset,
            [
                {
                    "external_id": example.id,
                    "feedback_text": example.feedback_text,
                    "expected_json": example.expected_json(),
                    "notes": example.notes,
                }
                for example in examples
            ],
        )
        self.repository.session.commit()
        self.repository.session.refresh(dataset)
        return dataset

    def _evaluate_example(
        self,
        *,
        run: EvaluationRun,
        persisted_example,
        example,
        prompt_version: str,
        top_k: int,
        provider: LLMProvider,
    ) -> dict:
        total_start = perf_counter()
        retrieval_latency_ms = None
        analysis_latency_ms = None
        retrieval_trace_id = None
        predicted_json = None
        metrics: dict = {"example_id": example.id, "expected": example.expected_json()}
        error_code = None
        error_message = None
        try:
            retrieval_start = perf_counter()
            retrieval = self.retrieval_service.search_with_options(
                example.feedback_text,
                top_k=top_k,
                persist_trace=True,
                feedback_record_id=None,
            )
            retrieval_latency_ms = _elapsed_ms(retrieval_start)
            retrieval_trace_id = retrieval.trace_id

            analysis_start = perf_counter()
            prompt = build_feedback_analysis_prompt(
                feedback_text=example.feedback_text,
                evidence=retrieval.results,
                prompt_version=prompt_version,
            )
            provider_response = provider.analyze_feedback(prompt)
            output = parse_structured_analysis(provider_response.raw_output)
            output = apply_confidence_policy(
                output,
                evidence=retrieval.results,
                threshold=self.settings.llm_confidence_threshold,
            )
            analysis_latency_ms = _elapsed_ms(analysis_start)
            predicted_json = output.model_dump(mode="json")

            retrieval_item_metrics = retrieval_metrics(example, retrieval.results, top_k)
            label_item_metrics = label_metrics(example, output)
            groundedness = groundedness_check(example, output, retrieval.results)
            workflow_item_metrics = workflow_metrics(example, output, self.settings.workflow_low_confidence_threshold)
            metrics.update(retrieval_item_metrics)
            metrics.update(label_item_metrics)
            metrics.update(workflow_item_metrics)
            metrics["groundedness_status"] = groundedness["status"]
            metrics["groundedness"] = groundedness
            metrics["predicted"] = predicted_json
            metrics["invalid_output"] = False
            metrics["provider_failed"] = False
        except AnalysisOutputParseError as exc:
            error_code = "invalid_output"
            error_message = exc.message
            metrics.update(label_metrics(example, None))
            metrics.update({"invalid_output": True, "provider_failed": False, "groundedness_status": "FAIL"})
        except Exception as exc:
            error_code = "evaluation_item_failed"
            error_message = str(exc)
            metrics.update(label_metrics(example, None))
            metrics.update({"invalid_output": False, "provider_failed": True, "groundedness_status": "FAIL"})
        total_latency_ms = _elapsed_ms(total_start)
        self.repository.create_run_item(
            evaluation_run_id=run.id,
            example_id=persisted_example.id if persisted_example else None,
            example_external_id=example.id,
            feedback_text=example.feedback_text,
            expected_json=example.expected_json(),
            predicted_json=predicted_json,
            retrieval_trace_id=retrieval_trace_id,
            analysis_run_id=None,
            metrics_json=metrics,
            error_code=error_code,
            error_message=error_message,
            retrieval_latency_ms=retrieval_latency_ms,
            analysis_latency_ms=analysis_latency_ms,
            total_latency_ms=total_latency_ms,
        )
        self.repository.session.commit()
        metrics["error_code"] = error_code
        metrics["error_message"] = error_message
        metrics["total_latency_ms"] = total_latency_ms
        return metrics


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)
