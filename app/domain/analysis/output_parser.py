import json

from pydantic import ValidationError

from app.domain.analysis.schemas import StructuredAnalysisOutput


class AnalysisOutputParseError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_structured_analysis(raw_output: str | dict) -> StructuredAnalysisOutput:
    if isinstance(raw_output, str):
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise AnalysisOutputParseError("LLM output was not valid JSON.") from exc
    else:
        payload = raw_output
    try:
        return StructuredAnalysisOutput.model_validate(payload)
    except ValidationError as exc:
        raise AnalysisOutputParseError("LLM output did not match the analysis schema.") from exc
