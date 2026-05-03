from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    path: str
    size_bytes: int


class StorageProvider(ABC):
    @abstractmethod
    def save(self, *, content: bytes, original_filename: str | None = None) -> StoredFile:
        raise NotImplementedError
