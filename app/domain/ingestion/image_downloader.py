import cv2
import numpy as np
import requests

from app.core.exceptions import DownloadError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.url_security import validate_public_http_url


class ImageDownloader:
    def __init__(self, timeout_seconds: float, max_image_bytes: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_image_bytes = max_image_bytes

    def download(self, url: str) -> np.ndarray:
        safe_url = validate_public_http_url(url)
        try:
            response = requests.get(safe_url, timeout=self.timeout_seconds, stream=True)
        except requests.RequestException as exc:
            raise DownloadError("Image URL could not be downloaded.") from exc

        if response.status_code >= 400:
            raise DownloadError("Image URL returned an unsuccessful status.", {"status_code": response.status_code})

        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        if not content_type.startswith("image/"):
            raise UnsupportedMediaTypeError("URL must point to an image resource.", {"content_type": content_type})

        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_image_bytes:
            raise PayloadTooLargeError("Image exceeds the configured maximum size.")

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > self.max_image_bytes:
                raise PayloadTooLargeError("Image exceeds the configured maximum size.")
            chunks.append(chunk)

        image_array = np.frombuffer(b"".join(chunks), dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise UnsupportedMediaTypeError("Downloaded content could not be decoded as an image.")
        return image

