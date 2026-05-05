import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.evaluation.models import EvaluationRun


class EvaluationReportGenerator:
    def __init__(self, report_dir: str | Path) -> None:
        self.report_dir = Path(report_dir)

    def write_reports(self, run: EvaluationRun, item_metrics: list[dict]) -> str:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        stem = f"evaluation_run_{run.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        json_path = self.report_dir / f"{stem}.json"
        markdown_path = self.report_dir / f"{stem}.md"
        payload = self._payload(run, item_metrics)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        markdown_path.write_text(self._markdown(payload), encoding="utf-8")
        return str(markdown_path)

    def _payload(self, run: EvaluationRun, item_metrics: list[dict]) -> dict:
        return {
            "run": {
                "id": run.id,
                "dataset_name": run.dataset_name,
                "dataset_version": run.dataset_version,
                "provider": run.provider,
                "model_name": run.model_name,
                "prompt_version": run.prompt_version,
                "vector_provider": run.vector_provider,
                "embedding_model": run.embedding_model,
                "top_k": run.top_k,
                "total_examples": run.total_examples,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            },
            "metrics": run.metrics_json or {},
            "failure_examples": [item for item in item_metrics if item.get("error_code")][:10],
            "incorrect_examples": [item for item in item_metrics if item.get("exact_label_match") is False][:10],
            "recommendations": self._recommendations(run.metrics_json or {}),
        }

    def _markdown(self, payload: dict) -> str:
        run = payload["run"]
        metrics = payload["metrics"]
        lines = [
            f"# FeedbackIQ Evaluation Run {run['id']}",
            "",
            f"- Dataset: {run['dataset_name']} ({run['dataset_version']})",
            f"- Provider/model: {run['provider']} / {run['model_name']}",
            f"- Prompt version: {run['prompt_version']}",
            f"- Retrieval: {run['vector_provider']} top_k={run['top_k']}",
            f"- Samples: {run['total_examples']}",
            "",
            "## Aggregate Metrics",
            "```json",
            json.dumps(metrics, indent=2),
            "```",
            "",
            "## Top Incorrect Examples",
        ]
        for item in payload["incorrect_examples"]:
            lines.append(f"- {item.get('example_id')}: expected={item.get('expected')} predicted={item.get('predicted')}")
        if not payload["incorrect_examples"]:
            lines.append("- None")
        lines.extend(["", "## Recommendations"])
        for recommendation in payload["recommendations"]:
            lines.append(f"- {recommendation}")
        return "\n".join(lines) + "\n"

    def _recommendations(self, metrics: dict) -> list[str]:
        recommendations: list[str] = []
        analysis = metrics.get("analysis", {})
        retrieval = metrics.get("retrieval", {})
        groundedness = metrics.get("groundedness", {})
        if retrieval.get("hit_at_k", 1.0) < 0.8:
            recommendations.append("Improve knowledge coverage, chunking, or top_k because retrieval hit rate is below target.")
        if analysis.get("exact_label_match_rate", 1.0) < 0.8:
            recommendations.append("Review prompt/provider behavior because exact label match is below target.")
        if groundedness.get("fail_rate", 0.0) > 0.0:
            recommendations.append("Inspect failed groundedness examples for missing evidence or unsupported model output.")
        if not recommendations:
            recommendations.append("No immediate quality regression was detected in this run.")
        return recommendations
