import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.dependencies import get_image_downloader, get_ingestion_service, get_pdf_text_extractor, get_storage_provider
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.ingestion.image_downloader import DownloadedImage
from app.domain.storage.local_storage_provider import LocalFileStorageProvider
from app.main import create_app


class FakeImageIngestionService:
    def __init__(self, text: str = "ocr text", should_fail: bool = False) -> None:
        self.text = text
        self.should_fail = should_fail

    def extract_from_bytes(self, content: bytes) -> str:
        if self.should_fail:
            from app.core.exceptions import OcrError

            raise OcrError("OCR failed in test.")
        return self.text

    def extract_from_image(self, image: np.ndarray) -> str:
        if self.should_fail:
            from app.core.exceptions import OcrError

            raise OcrError("OCR failed in test.")
        return self.text


class FakeImageDownloader:
    def download_image(self, url: str) -> DownloadedImage:
        if "localhost" in url:
            from app.core.exceptions import UnsafeUrlError

            raise UnsafeUrlError("Localhost image URLs are not allowed.")
        return DownloadedImage(
            content=b"fake image bytes",
            content_type="image/png",
            image=np.zeros((2, 2, 3), dtype=np.uint8),
        )


class FakePdfTextExtractor:
    def __init__(self, text: str = "pdf text", should_fail: bool = False) -> None:
        self.text = text
        self.should_fail = should_fail

    def extract_text(self, content: bytes) -> str:
        if self.should_fail:
            from app.core.exceptions import BadRequestError

            raise BadRequestError("PDF extraction failed in test.")
        return self.text


@pytest.fixture
def client_and_session_factory() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    storage_dir = Path.cwd() / f".test-ingestion-storage-{uuid4().hex}"

    def override_db_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_storage_provider] = lambda: LocalFileStorageProvider(str(storage_dir))
    app.dependency_overrides[get_ingestion_service] = lambda: FakeImageIngestionService("uploaded image text")
    app.dependency_overrides[get_image_downloader] = lambda: FakeImageDownloader()
    app.dependency_overrides[get_pdf_text_extractor] = lambda: FakePdfTextExtractor("pdf extracted text")
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_text_ingestion_creates_extracted_record(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post("/api/v1/ingestion/text", json={"text": "  Checkout   failed.  "})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_type"] == "TEXT"
    assert data["processing_status"] == "EXTRACTED"
    assert data["raw_text"] == "  Checkout   failed.  "
    assert data["normalized_text"] == "Checkout failed."


def test_image_upload_validation_rejects_non_image(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post(
        "/api/v1/ingestion/image",
        files={"file": ("feedback.txt", b"not image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_image_upload_ocr_success_persists_record(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, session_factory = client_and_session_factory

    response = client.post(
        "/api/v1/ingestion/image",
        files={"file": ("feedback.png", b"fake png", "image/png")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_type"] == "IMAGE"
    assert data["processing_status"] == "EXTRACTED"
    assert data["extracted_text"] == "uploaded image text"
    assert data["original_input_reference"].endswith(".png")
    with session_factory() as session:
        record = session.get(FeedbackRecord, data["feedback_id"])
    assert record is not None
    assert record.source_type == FeedbackSourceType.IMAGE


def test_image_upload_ocr_failure_persists_failed_record(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, session_factory = client_and_session_factory
    client.app.dependency_overrides[get_ingestion_service] = lambda: FakeImageIngestionService(should_fail=True)

    response = client.post(
        "/api/v1/ingestion/image",
        files={"file": ("feedback.png", b"fake png", "image/png")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["processing_status"] == "FAILED"
    assert data["error_code"] == "ocr_error"
    with session_factory() as session:
        record = session.scalar(select(FeedbackRecord).where(FeedbackRecord.id == data["feedback_id"]))
    assert record is not None
    assert record.processing_status == FeedbackProcessingStatus.FAILED


def test_image_url_validation_rejects_localhost(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post("/api/v1/ingestion/image-url", json={"url": "http://localhost/image.png"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsafe_url"


def test_image_url_success_stores_download_and_persists_record(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post("/api/v1/ingestion/image-url", json={"url": "https://example.com/image.png"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_type"] == "IMAGE"
    assert data["raw_text"] == "https://example.com/image.png"
    assert data["extracted_text"] == "uploaded image text"


def test_pdf_upload_validation_rejects_non_pdf(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post(
        "/api/v1/ingestion/pdf",
        files={"file": ("feedback.txt", b"text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_pdf_upload_success_with_fake_extractor(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post(
        "/api/v1/ingestion/pdf",
        files={"file": ("feedback.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_type"] == "PDF"
    assert data["processing_status"] == "EXTRACTED"
    assert data["normalized_text"] == "pdf extracted text"


def test_csv_ingestion_creates_valid_rows_and_reports_invalid_rows(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory
    csv_content = b"text\nCheckout failed.\n   \nShipping delayed.\n"

    response = client.post(
        "/api/v1/ingestion/csv",
        files={"file": ("feedback.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["created_count"] == 2
    assert data["failed_count"] == 1
    assert len(data["feedback_ids"]) == 2
    assert data["row_errors"][0]["row_number"] == 3


def test_csv_missing_text_column_returns_bad_request(client_and_session_factory: tuple[TestClient, sessionmaker[Session]]):
    client, _ = client_and_session_factory

    response = client.post(
        "/api/v1/ingestion/csv",
        files={"file": ("feedback.csv", b"message\nhello\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
