from app.core.exceptions import ModelUnavailableError
from app.domain.sentiment.sentiment_analyzer import SentimentAnalyzer, SentimentResult


class HuggingFaceSentimentAnalyzer(SentimentAnalyzer):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise ModelUnavailableError("transformers is not installed.") from exc
            self._pipeline = pipeline("sentiment-analysis", model=self.model_name)
        return self._pipeline

    def analyze(self, text: str) -> SentimentResult:
        result = self.pipeline(text)[0]
        return SentimentResult(label=result["label"], score=float(result["score"]))

