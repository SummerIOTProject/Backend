from __future__ import annotations

from app.core.config import settings
from app.services.storage.base import ImageStorage
from app.services.storage.local_storage import LocalImageStorage
from app.services.storage.vercel_blob_storage import VercelBlobStorage


def build_image_storage() -> ImageStorage:
    if settings.STORAGE_BACKEND == "LOCAL":
        return LocalImageStorage()
    if settings.STORAGE_BACKEND == "VERCEL_BLOB":
        return VercelBlobStorage()
    raise ValueError(f"Unsupported STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
