from typing import Any


class FeedbackIQError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class BadRequestError(FeedbackIQError):
    status_code = 400
    code = "bad_request"


class UnsafeUrlError(BadRequestError):
    code = "unsafe_url"


class DownloadError(FeedbackIQError):
    status_code = 502
    code = "download_error"


class UnsupportedMediaTypeError(FeedbackIQError):
    status_code = 415
    code = "unsupported_media_type"


class PayloadTooLargeError(FeedbackIQError):
    status_code = 413
    code = "payload_too_large"


class OcrError(FeedbackIQError):
    status_code = 422
    code = "ocr_error"


class ModelUnavailableError(FeedbackIQError):
    status_code = 503
    code = "model_unavailable"

