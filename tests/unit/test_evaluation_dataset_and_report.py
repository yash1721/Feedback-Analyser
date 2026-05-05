import json
import shutil
from pathlib import Path

from app.domain.evaluation.datasets import EvaluationDatasetLoader
from app.domain.evaluation.models import EvaluationRun
from app.domain.evaluation.report import EvaluationReportGenerator


def test_dataset_loader_reads_fixture():
    dataset = EvaluationDatasetLoader().load()

    assert dataset.name == "feedbackiq_seed"
    assert dataset.examples
    assert dataset.examples[0].feedback_text


def test_report_generator_writes_json_and_markdown():
    report_dir = Path(".test_eval_report_unit")
    shutil.rmtree(report_dir, ignore_errors=True)
    run = EvaluationRun(
        id=1,
        dataset_name="seed",
        dataset_version="v1",
        provider="fake",
        model_name="fake-feedback-analyzer",
        prompt_version="feedback-analysis-v1",
        vector_provider="faiss",
        embedding_model="test",
        top_k=3,
        total_examples=1,
        metrics_json={"analysis": {"exact_label_match_rate": 1.0}},
    )

    markdown_path = EvaluationReportGenerator(report_dir).write_reports(run, [])

    try:
        assert "evaluation_run_1" in markdown_path
        assert "FeedbackIQ Evaluation Run 1" in Path(markdown_path).read_text(encoding="utf-8")
        json_reports = list(report_dir.glob("evaluation_run_1_*.json"))
        assert json.loads(json_reports[0].read_text(encoding="utf-8"))["run"]["id"] == 1
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)
