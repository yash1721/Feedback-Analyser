from fastapi.testclient import TestClient

from app.main import create_app


def test_feedback_analyze_rejects_empty_text():
    client = TestClient(create_app())

    response = client.post("/api/v1/feedback/analyze", json={"text": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_ocr_upload_rejects_non_image_file():
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/ocr/extract",
        files={"file": ("feedback.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_ocr_url_rejects_localhost():
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/ocr/extract-from-url",
        json={"url": "http://localhost/image.png"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsafe_url"
