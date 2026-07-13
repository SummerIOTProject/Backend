from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.services.storage.base import ImageStorage
from app.utils.enums import ImageType


class LocalImageStorage(ImageStorage):
    backend_name = "LOCAL"

    def build_key(self, *, meal_record_id: int, image_type: ImageType, filename: str) -> str:  # noqa: ARG002
        return f"{image_type.value.lower()}/{filename}"

    def save(self, *, key: str, content: bytes, content_type: str) -> str:  # noqa: ARG002
        path = self.resolve_local_path(key)
        if path is None:
            raise RuntimeError("Local storage path resolution failed.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def read(self, key: str) -> bytes:
        path = self.resolve_local_path(key)
        if path is None or not path.exists():
            raise NotFoundException(message="이미지 파일을 찾을 수 없습니다.", code="IMAGE_FILE_NOT_FOUND", detail="storage key missing")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self.resolve_local_path(key)
        if path is not None and path.exists() and path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        path = self.resolve_local_path(key)
        return bool(path and path.exists())

    def ensure_ready(self) -> None:
        root = settings.upload_path
        probe = None
        try:
            root.mkdir(parents=True, exist_ok=True)
            for child in ("before", "after"):
                (root / child).mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=root, prefix=".write-test-", delete=False) as tmp:
                tmp.write(b"ok")
                probe = Path(tmp.name)
            if probe is not None and probe.exists():
                probe.unlink()
        except OSError as exc:
            if probe is not None and probe.exists():
                probe.unlink()
            raise RuntimeError("Upload storage is not writable.") from exc

    def validate_configuration(self) -> None:
        self.ensure_ready()

    def resolve_local_path(self, key: str) -> Path | None:
        safe_root = Path(settings.UPLOAD_DIR).resolve()
        candidate = (safe_root / key).resolve()
        if not str(candidate).startswith(str(safe_root)):
            raise BadRequestException(message="잘못된 파일 경로입니다.", code="IMAGE_NOT_FOUND", detail="invalid storage path")
        return candidate
