from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import BadRequestException, NotFoundException, ServerException
from app.services.storage.factory import build_image_storage
from app.services.storage.local_storage import LocalImageStorage
from app.services.storage.vercel_blob_storage import VercelBlobStorage
from app.utils.enums import ImageType


class FakeBlobError(Exception):
    def __init__(self, status_code: int, message: str = "blob error"):
        super().__init__(message)
        self.status_code = status_code


class FakeBlobNotFoundError(Exception):
    pass


class FakeBlobAccessError(Exception):
    pass


class FakeBlobNoTokenProvidedError(Exception):
    pass


class FakeBlobServiceNotAvailable(Exception):
    pass


class FakeBlobServiceRateLimited(Exception):
    pass


class FakeBlobStoreSuspendedError(Exception):
    pass


def make_http_status_error(status_code: int):
    request = httpx.Request("GET", "https://example.invalid/blob")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("blob request failed", request=request, response=response)


class FakeBlobClient:
    last_instance = None
    NONE = object()

    def __init__(self, token=None):
        self.token = token
        self.put_calls = []
        self.get_calls = []
        self.head_calls = []
        self.delete_calls = []
        self.closed = False
        self.behavior = {}
        FakeBlobClient.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

    def put(self, pathname, content, *, access, content_type, add_random_suffix, overwrite=False, cache_control_max_age=None, multipart=False, on_upload_progress=None):
        self.put_calls.append(
            {
                "pathname": pathname,
                "content": content,
                "access": access,
                "content_type": content_type,
                "add_random_suffix": add_random_suffix,
                "overwrite": overwrite,
            }
        )
        effect = self.behavior.get("put")
        if isinstance(effect, Exception):
            raise effect
        return effect if effect is not None else SimpleNamespace(pathname=pathname, url="https://store.private.blob.vercel-storage.com/" + pathname)

    def get(self, target, *, access="public", timeout=None, use_cache=True, if_none_match=None):
        self.get_calls.append(
            {
                "target": target,
                "access": access,
                "timeout": timeout,
                "use_cache": use_cache,
                "if_none_match": if_none_match,
            }
        )
        effect = self.behavior.get("get")
        if isinstance(effect, Exception):
            raise effect
        if effect is self.NONE:
            return None
        return effect if effect is not None else b"image-bytes"

    def head(self, target):
        self.head_calls.append(target)
        effect = self.behavior.get("head")
        if isinstance(effect, Exception):
            raise effect
        return effect if effect is not None else SimpleNamespace(pathname="meal-images/1/before/test.jpg")

    def delete(self, target_or_targets):
        self.delete_calls.append(target_or_targets)
        effect = self.behavior.get("delete")
        if isinstance(effect, Exception):
            raise effect
        return effect


def _make_storage(monkeypatch, *, token="token", vercel=False):
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobClient", FakeBlobClient)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobNotFoundError", FakeBlobNotFoundError)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobAccessError", FakeBlobAccessError)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobNoTokenProvidedError", FakeBlobNoTokenProvidedError)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobServiceNotAvailable", FakeBlobServiceNotAvailable)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobServiceRateLimited", FakeBlobServiceRateLimited)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobStoreSuspendedError", FakeBlobStoreSuspendedError)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_STORE_ID", "")
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_READ_WRITE_TOKEN", token)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.VERCEL_OIDC_TOKEN", "oidc-token")
    if vercel:
        monkeypatch.setenv("VERCEL", "1")
    else:
        monkeypatch.delenv("VERCEL", raising=False)
    return VercelBlobStorage()


def test_storage_factory_selects_local(monkeypatch):
    monkeypatch.setattr("app.services.storage.factory.settings.STORAGE_BACKEND", "LOCAL")
    assert isinstance(build_image_storage(), LocalImageStorage)


def test_storage_factory_selects_vercel_blob(monkeypatch):
    monkeypatch.setattr("app.services.storage.factory.settings.STORAGE_BACKEND", "VERCEL_BLOB")
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobClient", FakeBlobClient)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_STORE_ID", "")
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_READ_WRITE_TOKEN", "token")
    monkeypatch.delenv("VERCEL", raising=False)
    assert isinstance(build_image_storage(), VercelBlobStorage)


def test_storage_factory_rejects_unknown(monkeypatch):
    monkeypatch.setattr("app.services.storage.factory.settings.STORAGE_BACKEND", "UNKNOWN")
    with pytest.raises(ValueError):
        build_image_storage()


def test_local_storage_save_read_delete_exists(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.local_storage.settings.UPLOAD_DIR", str(tmp_path / "uploads"))
    storage = LocalImageStorage()
    key = storage.build_key(meal_record_id=1, image_type=ImageType.BEFORE, filename="test.jpg")
    storage.save(key=key, content=b"hello", content_type="image/jpeg")
    assert storage.exists(key) is True
    assert storage.read(key) == b"hello"
    storage.delete(key)
    assert storage.exists(key) is False


def test_local_storage_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.local_storage.settings.UPLOAD_DIR", str(tmp_path / "uploads"))
    storage = LocalImageStorage()
    with pytest.raises(Exception):
        storage.read("before/missing.jpg")


def test_vercel_blob_storage_missing_auth_fails(monkeypatch):
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobClient", FakeBlobClient)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_STORE_ID", "")
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_READ_WRITE_TOKEN", None)
    monkeypatch.delenv("VERCEL", raising=False)
    storage = VercelBlobStorage()
    with pytest.raises(RuntimeError):
        storage.validate_configuration()


def test_importlib_removed_and_blobclient_used():
    content = Path("app/services/storage/vercel_blob_storage.py").read_text(encoding="utf-8")
    assert "importlib" not in content
    assert "from vercel.blob import BlobClient" in content
    assert 'import_module("vercel")' not in content


def test_blobclient_created_with_read_write_token(monkeypatch):
    storage = _make_storage(monkeypatch, token="blob-token", vercel=False)
    client = storage._create_client()
    assert isinstance(client, FakeBlobClient)
    assert client.token == "blob-token"


def test_blobclient_created_without_token_on_vercel(monkeypatch):
    storage = _make_storage(monkeypatch, token=None, vercel=True)
    with pytest.raises(RuntimeError):
        storage._create_client()


def test_oidc_token_not_passed_as_blobclient_token(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = storage._create_client()
    assert client.token == "token"


def test_sanitize_key_rejects_invalid_paths(monkeypatch):
    storage = _make_storage(monkeypatch)
    assert storage._sanitize_key("meal-images/1/before/uuid.jpg") == "meal-images/1/before/uuid.jpg"
    for bad_key in ["", "/secret.jpg", "//secret.jpg", "../secret.jpg", "meal-images/../../secret.jpg", "meal-images/./secret.jpg", "meal-images//secret.jpg", r"meal-images\\secret", "http://example.com/x", "https://example.com/x"]:
        with pytest.raises(BadRequestException):
            storage._sanitize_key(bad_key)


def test_save_uses_blobclient_put(monkeypatch):
    storage = _make_storage(monkeypatch)
    key = storage.build_key(meal_record_id=1, image_type=ImageType.BEFORE, filename="test.jpg")
    returned = storage.save(key=key, content=b"abc", content_type="image/jpeg")
    client = FakeBlobClient.last_instance
    assert returned == key
    assert client.put_calls[0]["pathname"] == key
    assert client.put_calls[0]["content"] == b"abc"
    assert client.put_calls[0]["access"] == "private"
    assert client.put_calls[0]["content_type"] == "image/jpeg"
    assert client.put_calls[0]["add_random_suffix"] is False
    assert client.closed is True


def test_read_uses_blobclient_get_and_returns_bytes(monkeypatch):
    storage = _make_storage(monkeypatch)
    key = storage.build_key(meal_record_id=1, image_type=ImageType.AFTER, filename="test.jpg")
    result = storage.read(key)
    client = FakeBlobClient.last_instance
    assert result == b"image-bytes"
    assert client.get_calls[0]["target"] == key
    assert client.get_calls[0]["access"] == "private"
    assert client.closed is True


def test_read_none_raises_image_not_found(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = FakeBlobClient.NONE
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(NotFoundException):
        storage.read("meal-images/1/before/test.jpg")


def test_read_auth_error_not_mapped_to_not_found(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = FakeBlobAccessError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.read("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_AUTHENTICATION_FAILED"


def test_read_blob_not_found_uses_sdk_exception(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = FakeBlobNotFoundError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(NotFoundException):
        storage.read("meal-images/1/before/test.jpg")


def test_exists_uses_head_not_get(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    assert storage.exists("meal-images/1/before/test.jpg") is True
    assert client.head_calls == ["meal-images/1/before/test.jpg"]
    assert client.get_calls == []


def test_exists_returns_false_only_for_not_found(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["head"] = FakeBlobNotFoundError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    assert storage.exists("meal-images/1/before/test.jpg") is False


def test_exists_auth_error_raises(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["head"] = FakeBlobAccessError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.exists("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_AUTHENTICATION_FAILED"


def test_delete_uses_blobclient_delete(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    storage.delete("meal-images/1/before/test.jpg")
    assert client.delete_calls == ["meal-images/1/before/test.jpg"]


def test_delete_not_found_is_idempotent(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["delete"] = FakeBlobNotFoundError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    storage.delete("meal-images/1/before/test.jpg")


def test_delete_auth_error_raises(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["delete"] = FakeBlobNoTokenProvidedError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.delete("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_AUTHENTICATION_FAILED"


def test_service_unavailable_maps_to_storage_unavailable(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["head"] = FakeBlobServiceNotAvailable()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.exists("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_UNAVAILABLE"


def test_rate_limited_maps_to_storage_unavailable(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = FakeBlobServiceRateLimited()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.read("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_UNAVAILABLE"


def test_store_suspended_maps_to_storage_unavailable(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["delete"] = FakeBlobStoreSuspendedError()
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.delete("meal-images/1/before/test.jpg")
    assert exc_info.value.code == "STORAGE_UNAVAILABLE"


def test_context_manager_closed_on_error(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = FakeBlobError(503)
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException):
        storage.read("meal-images/1/before/test.jpg")
    assert client.closed is True


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (FakeBlobError(429), 429),
        (make_http_status_error(503), 503),
        (FakeBlobError("429"), None),
        (Exception("no status"), None),
    ],
)
def test_get_status_code_handles_status_and_response(exc, expected):
    assert VercelBlobStorage._get_status_code(exc) == expected


def test_get_status_code_prefers_exc_status_code_over_response():
    error = make_http_status_error(503)
    error.status_code = 401
    assert VercelBlobStorage._get_status_code(error) == 401


def test_get_status_code_ignores_string_response_status():
    error = Exception("bad response")
    error.response = SimpleNamespace(status_code="404")  # type: ignore[attr-defined]
    assert VercelBlobStorage._get_status_code(error) is None


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, "STORAGE_REQUEST_INVALID"),
        (401, "STORAGE_AUTHENTICATION_FAILED"),
        (403, "STORAGE_PERMISSION_DENIED"),
        (429, "STORAGE_UNAVAILABLE"),
        (503, "STORAGE_UNAVAILABLE"),
    ],
)
def test_http_status_error_fallback_maps_read_errors(monkeypatch, status_code, expected_code):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = make_http_status_error(status_code)
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(ServerException) as exc_info:
        storage.read("meal-images/1/before/test.jpg")
    assert exc_info.value.code == expected_code


def test_http_status_error_404_read_maps_to_image_not_found(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["get"] = make_http_status_error(404)
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    with pytest.raises(NotFoundException):
        storage.read("meal-images/1/before/test.jpg")


def test_http_status_error_404_exists_returns_false(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["head"] = make_http_status_error(404)
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    assert storage.exists("meal-images/1/before/test.jpg") is False


def test_http_status_error_404_delete_is_idempotent(monkeypatch):
    storage = _make_storage(monkeypatch)
    client = FakeBlobClient()
    client.behavior["delete"] = make_http_status_error(404)
    monkeypatch.setattr(storage, "_create_client", lambda: client)
    storage.delete("meal-images/1/before/test.jpg")


def test_production_settings_require_postgres_and_blob_on_vercel():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DATABASE_URL="sqlite:///./meal_service.db",
            STORAGE_BACKEND="LOCAL",
            JWT_SECRET_KEY="x" * 40,
            DEVICE_API_KEY="y" * 40,
            CORS_ORIGINS=["https://example.com"],
        )


def test_vercel_runtime_still_requires_read_write_token():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="development",
            STORAGE_BACKEND="VERCEL_BLOB",
            BLOB_STORE_ID="store",
            BLOB_READ_WRITE_TOKEN="",
            VERCEL_OIDC_TOKEN="oidc-only",
        )


def test_vercel_blob_settings_allow_missing_store_id():
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        STORAGE_BACKEND="VERCEL_BLOB",
        BLOB_STORE_ID="",
        BLOB_READ_WRITE_TOKEN="token",
    )
    assert settings.STORAGE_BACKEND == "VERCEL_BLOB"


def test_vercel_blob_settings_store_id_without_token_fails():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="development",
            STORAGE_BACKEND="VERCEL_BLOB",
            BLOB_STORE_ID="store-id",
            BLOB_READ_WRITE_TOKEN="",
        )


def test_blobclient_import_missing_fails(monkeypatch):
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.BlobClient", None)
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_STORE_ID", "")
    monkeypatch.setattr("app.services.storage.vercel_blob_storage.settings.BLOB_READ_WRITE_TOKEN", "token")
    storage = VercelBlobStorage()
    with pytest.raises(RuntimeError):
        storage.validate_configuration()
