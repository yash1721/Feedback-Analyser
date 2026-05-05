import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.analytics.schemas import AnalyticsReportResponse, ExecutiveSummaryResponse


class AnalyticsReportGenerator:
    def __init__(self, report_dir: str | Path) -> None:
        self.report_dir = Path(report_dir)

    def write_report(self, *, payload: dict, executive_summary: ExecutiveSummaryResponse, format: str = "markdown") -> AnalyticsReportResponse:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(timezone.utc)
        stem = f"analytics_summary_{generated_at.strftime('%Y%m%d%H%M%S')}"
        json_path = self.report_dir / f"{stem}.json"
        md_path = self.report_dir / f"{stem}.md"
        json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        md_path.write_text(self._markdown(payload), encoding="utf-8")
        selected_path = md_path if format == "markdown" else json_path
        return AnalyticsReportResponse(
            format=format,
            report_path=str(selected_path),
            generated_at=generated_at,
            executive_summary=executive_summary,
        )

    def _markdown(self, payload: dict) -> str:
        executive = payload["executive_summary"]
        lines = [
            "# FeedbackIQ Analytics Summary",
            "",
            executive["summary_text"],
            "",
            "## Key Findings",
        ]
        lines.extend([f"- {item}" for item in executive["key_findings"]])
        lines.extend(["", "## Risk Flags"])
        risk_flags = executive.get("risk_flags") or []
        lines.extend([f"- {item}" for item in risk_flags] or ["- None"])
        lines.extend(["", "## Metrics Payload", "```json", json.dumps(payload, indent=2, default=str), "```"])
        return "\n".join(lines) + "\n"
