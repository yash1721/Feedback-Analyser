from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


class SentimentAnalyzer(ABC):
    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        raise NotImplementedError


class FakeSentimentAnalyzer(SentimentAnalyzer):
    def __init__(self, label: str = "POSITIVE", score: float = 1.0) -> None:
        self.label = label
        self.score = score

    def analyze(self, text: str) -> SentimentResult:
        return SentimentResult(label=self.label, score=self.score)

