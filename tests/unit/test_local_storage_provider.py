import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.storage.local_storage_provider import LocalFileStorageProvider


@pytest.fixture
def storage_dir() -> Iterator[Path]:
    path = Path.cwd() / f".test-storage-{uuid4().hex}"
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_local_storage_provider_saves_with_safe_generated_name(storage_dir: Path):
    provider = LocalFileStorageProvider(str(storage_dir))

    stored = provider.save(content=b"hello", original_filename="../../feedback.PNG")

    assert stored.size_bytes == 5
    assert stored.storage_key.endswith(".png")
    assert ".." not in stored.storage_key
    assert (storage_dir / stored.storage_key).read_bytes() == b"hello"


def test_local_storage_provider_ignores_unsafe_extension(storage_dir: Path):
    provider = LocalFileStorageProvider(str(storage_dir))

    stored = provider.save(content=b"hello", original_filename="feedback.bad/ext")

    assert "." not in stored.storage_key
