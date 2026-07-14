from __future__ import annotations

from typing import NoReturn

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException, ServerException
from app.services.storage.base import ImageStorage
from app.utils.enums import ImageType

try:
    from vercel.blob import BlobClient
    from vercel.blob.errors import (
        BlobAccessError,
        BlobNoTokenProvidedError,
        BlobNotFoundError,
        BlobRequestAbortedError,
        BlobServiceNotAvailable,
        BlobServiceRateLimited,
        BlobStoreNotFoundError,
        BlobStoreSuspendedError,
    )
except ImportError:  # pragma: no cover
    BlobClient = None
    BlobAccessError = BlobNoTokenProvidedError = BlobNotFoundError = None
    BlobRequestAbortedError = BlobServiceNotAvailable = BlobServiceRateLimited = None
    BlobStoreNotFoundError = BlobStoreSuspendedError = None


class VercelBlobStorage(ImageStorage):
    backend_name = "VERCEL_BLOB"

    def __init__(self) -> None:
        self.read_write_token = settings.BLOB_READ_WRITE_TOKEN
        self.oidc_token = settings.VERCEL_OIDC_TOKEN

    def build_key(self, *, meal_record_id: int, image_type: ImageType, filename: str) -> str:
        return f"meal-images/{meal_record_id}/{image_type.value.lower()}/{filename}"

    def save(self, *, key: str, content: bytes, content_type: str) -> str:
        self.validate_configuration()
        self._put_blob(key=key, content=content, content_type=content_type)
        return key

    def read(self, key: str) -> bytes:
        self.validate_configuration()
        data = self._read_blob(key)
        if data is None:
            raise NotFoundException(message="이미지 파일을 찾을 수 없습니다.", code="IMAGE_FILE_NOT_FOUND", detail="blob missing")
        return data

    def delete(self, key: str) -> None:
        self.validate_configuration()
        self._delete_blob(key)

    def exists(self, key: str) -> bool:
        self.validate_configuration()
        metadata = self._head_blob(key)
        return metadata is not None

    def ensure_ready(self) -> None:
        self.validate_configuration()

    def validate_configuration(self) -> None:
        if BlobClient is None:
            raise RuntimeError("Vercel Blob SDK is not installed. Install the 'vercel' package.")
        if not self.read_write_token:
            raise RuntimeError("BLOB_READ_WRITE_TOKEN is not configured.")

    def _create_client(self):
        self.validate_configuration()
        return BlobClient(token=self.read_write_token)

    def _sanitize_key(self, key: str) -> str:
        raw_key = key.strip()
        if not raw_key:
            raise BadRequestException(message="잘못된 이미지 저장 경로입니다.", code="IMAGE_NOT_FOUND", detail="empty storage key")
        if raw_key.startswith("/"):
            raise BadRequestException(message="잘못된 이미지 저장 경로입니다.", code="IMAGE_NOT_FOUND", detail="absolute path is not allowed")
        if raw_key.startswith(("http://", "https://")):
            raise BadRequestException(message="잘못된 이미지 저장 경로입니다.", code="IMAGE_NOT_FOUND", detail="absolute url is not allowed")
        if "\\" in raw_key:
            raise BadRequestException(message="잘못된 이미지 저장 경로입니다.", code="IMAGE_NOT_FOUND", detail="backslash is not allowed")
        parts = raw_key.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise BadRequestException(message="잘못된 이미지 저장 경로입니다.", code="IMAGE_NOT_FOUND", detail="invalid path segments")
        return raw_key

    @staticmethod
    def _get_status_code(exc: Exception) -> int | None:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        response_status_code = getattr(response, "status_code", None)
        if isinstance(response_status_code, int):
            return response_status_code
        return None

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        if BlobNotFoundError is not None and isinstance(exc, BlobNotFoundError):
            return True
        return VercelBlobStorage._get_status_code(exc) == 404

    @staticmethod
    def _raise_storage_error(exc: Exception, *, operation: str) -> NoReturn:
        detail = f"{operation}:{type(exc).__name__}"
        status_code = VercelBlobStorage._get_status_code(exc)
        if BlobAccessError is not None and isinstance(exc, (BlobAccessError, BlobNoTokenProvidedError)):
            raise ServerException(message="이미지 저장소 인증에 실패했습니다.", code="STORAGE_AUTHENTICATION_FAILED", detail=detail) from exc
        if BlobStoreNotFoundError is not None and isinstance(exc, BlobStoreNotFoundError):
            raise ServerException(message="이미지 저장소 설정이 올바르지 않습니다.", code="STORAGE_CONFIGURATION_ERROR", detail=detail) from exc
        if BlobStoreSuspendedError is not None and isinstance(exc, BlobStoreSuspendedError):
            raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail=detail) from exc
        if BlobServiceNotAvailable is not None and isinstance(exc, BlobServiceNotAvailable):
            raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail=detail) from exc
        if BlobServiceRateLimited is not None and isinstance(exc, BlobServiceRateLimited):
            raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail=detail) from exc
        if BlobRequestAbortedError is not None and isinstance(exc, BlobRequestAbortedError):
            raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail=detail) from exc
        if status_code == 401:
            raise ServerException(message="이미지 저장소 인증에 실패했습니다.", code="STORAGE_AUTHENTICATION_FAILED", detail=detail) from exc
        if status_code == 403:
            raise ServerException(message="이미지 저장소 권한이 없습니다.", code="STORAGE_PERMISSION_DENIED", detail=detail) from exc
        if status_code == 400:
            raise ServerException(message="이미지 저장소 요청 형식이 올바르지 않습니다.", code="STORAGE_REQUEST_INVALID", detail=detail) from exc
        raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail=detail) from exc

    def _put_blob(self, *, key: str, content: bytes, content_type: str) -> None:
        normalized_key = self._sanitize_key(key)
        try:
            with self._create_client() as client:
                result = client.put(
                    normalized_key,
                    content,
                    access="private",
                    content_type=content_type,
                    add_random_suffix=False,
                    overwrite=False,
                )
        except Exception as exc:  # noqa: BLE001
            self._raise_storage_error(exc, operation="upload")
        if result is None:
            raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail="upload:empty_result")

    def _read_blob(self, key: str) -> bytes | None:
        normalized_key = self._sanitize_key(key)
        try:
            with self._create_client() as client:
                content = client.get(normalized_key, access="private")
        except Exception as exc:  # noqa: BLE001
            if self._is_not_found_error(exc):
                return None
            self._raise_storage_error(exc, operation="read")
        if content is None:
            return None
        if isinstance(content, bytes):
            return content
        payload = getattr(content, "content", None)
        if isinstance(payload, bytes):
            return payload
        if hasattr(content, "read"):
            return content.read()
        raise ServerException(message="이미지 저장소를 사용할 수 없습니다.", code="STORAGE_UNAVAILABLE", detail="read:unexpected_response_type")

    def _head_blob(self, key: str):
        normalized_key = self._sanitize_key(key)
        try:
            with self._create_client() as client:
                return client.head(normalized_key)
        except Exception as exc:  # noqa: BLE001
            if self._is_not_found_error(exc):
                return None
            self._raise_storage_error(exc, operation="head")

    def _delete_blob(self, key: str) -> None:
        normalized_key = self._sanitize_key(key)
        try:
            with self._create_client() as client:
                client.delete(normalized_key)
        except Exception as exc:  # noqa: BLE001
            if self._is_not_found_error(exc):
                return
            self._raise_storage_error(exc, operation="delete")
