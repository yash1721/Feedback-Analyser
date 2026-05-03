from pathlib import Path
from uuid import uuid4

from app.domain.storage.storage_provider import StorageProvider, StoredFile


class LocalFileStorageProvider(StorageProvider):
    def __init__(self, storage_dir: str) -> None:
        self.storage_dir = Path(storage_dir)

    def save(self, *, content: bytes, original_filename: str | None = None) -> StoredFile:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        extension = self._safe_extension(original_filename)
        storage_key = f"{uuid4().hex}{extension}"
        path = self.storage_dir / storage_key
        path.write_bytes(content)
        return StoredFile(storage_key=storage_key, path=str(path), size_bytes=len(content))

    @staticmethod
    def _safe_extension(original_filename: str | None) -> str:
        if not original_filename:
            return ""
        suffix = Path(original_filename).suffix.lower()
        if len(suffix) > 16:
            return ""
        if not suffix.startswith("."):
            return ""
        if not all(character.isalnum() or character == "." for character in suffix):
            return ""
        return suffix
