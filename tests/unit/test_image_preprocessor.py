import numpy as np

from app.domain.ingestion.image_preprocessor import ImagePreprocessor


def test_preprocess_for_ocr_returns_single_channel_image():
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    processed = ImagePreprocessor().preprocess_for_ocr(image)

    assert processed.shape == (10, 10)

