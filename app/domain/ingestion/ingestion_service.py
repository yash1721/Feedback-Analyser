import cv2
import numpy as np

from app.core.exceptions import UnsupportedMediaTypeError
from app.domain.ingestion.image_downloader import ImageDownloader
from app.domain.ingestion.image_preprocessor import ImagePreprocessor
from app.domain.ingestion.ocr_engine import OcrEngine


class IngestionService:
    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        ocr_engine: OcrEngine,
        downloader: ImageDownloader | None = None,
    ) -> None:
        self.preprocessor = preprocessor
        self.ocr_engine = ocr_engine
        self.downloader = downloader

    def extract_from_bytes(self, image_bytes: bytes) -> str:
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise UnsupportedMediaTypeError("Uploaded content could not be decoded as an image.")
        return self.extract_from_image(image)

    def extract_from_url(self, url: str) -> str:
        if self.downloader is None:
            raise RuntimeError("ImageDownloader is required for URL extraction.")
        return self.extract_from_image(self.downloader.download(url))

    def extract_from_image(self, image: np.ndarray) -> str:
        processed = self.preprocessor.preprocess_for_ocr(image)
        return self.ocr_engine.extract_text(processed)

