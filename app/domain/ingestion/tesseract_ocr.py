import numpy as np

from app.core.exceptions import OcrError
from app.domain.ingestion.ocr_engine import OcrEngine


class TesseractOcrEngine(OcrEngine):
    def __init__(self, languages: str = "eng+hin", timeout_seconds: int = 5) -> None:
        self.languages = languages
        self.timeout_seconds = timeout_seconds

    def extract_text(self, image: np.ndarray) -> str:
        config = f"-l {self.languages} --oem 3 --psm 6"
        try:
            import pytesseract

            return pytesseract.image_to_string(image, config=config, timeout=self.timeout_seconds).strip()
        except ImportError as exc:
            raise OcrError("pytesseract is not installed.") from exc
        except RuntimeError as exc:
            raise OcrError("OCR processing timed out or failed.") from exc
        except Exception as exc:
            if exc.__class__.__name__ == "TesseractNotFoundError":
                raise OcrError("Tesseract binary is not installed or not available on PATH.") from exc
            raise

