from abc import ABC, abstractmethod

import numpy as np


class OcrEngine(ABC):
    @abstractmethod
    def extract_text(self, image: np.ndarray) -> str:
        raise NotImplementedError


class FakeOcrEngine(OcrEngine):
    def __init__(self, text: str = "fake ocr text") -> None:
        self.text = text

    def extract_text(self, image: np.ndarray) -> str:
        return self.text

