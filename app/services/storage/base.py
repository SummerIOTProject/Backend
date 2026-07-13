from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.utils.enums import ImageType


class ImageStorage(ABC):
    backend_name: str

    @abstractmethod
    def build_key(self, *, meal_record_id: int, image_type: ImageType, filename: str) -> str:
        ...

    @abstractmethod
    def save(self, *, key: str, content: bytes, content_type: str) -> str:
        ...

    @abstractmethod
    def read(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def ensure_ready(self) -> None:
        ...

    @abstractmethod
    def validate_configuration(self) -> None:
        ...

    def resolve_local_path(self, key: str) -> Path | None:
        return None
