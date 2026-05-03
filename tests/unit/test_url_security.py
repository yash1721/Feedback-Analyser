import socket

import pytest

from app.core.exceptions import UnsafeUrlError
from app.core.url_security import validate_public_http_url


def test_rejects_non_http_urls():
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("file:///tmp/image.png")


def test_rejects_localhost():
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("http://localhost/image.png")


def test_rejects_private_ip():
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url("http://127.0.0.1/image.png")


def test_accepts_public_http_url(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))],
    )

    assert validate_public_http_url("https://example.com/image.png") == "https://example.com/image.png"

