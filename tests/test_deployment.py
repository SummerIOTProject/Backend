from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.runtime import ensure_upload_storage_ready


def test_production_default_jwt_secret_fails():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="sqlite:///./meal_service.db",
            JWT_SECRET_KEY="replace-with-secure-secret",
            DEVICE_API_KEY="x" * 40,
            CORS_ORIGINS=["https://example.com"],
        )


def test_production_default_device_key_fails():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="sqlite:///./meal_service.db",
            JWT_SECRET_KEY="x" * 40,
            DEVICE_API_KEY="replace-with-device-key",
            CORS_ORIGINS=["https://example.com"],
        )


def test_production_same_secrets_fail():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="sqlite:///./meal_service.db",
            JWT_SECRET_KEY="x" * 40,
            DEVICE_API_KEY="x" * 40,
            CORS_ORIGINS=["https://example.com"],
        )


def test_openai_vlm_requires_api_key_outside_development():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="sqlite:///./meal_service.db",
            JWT_SECRET_KEY="x" * 40,
            DEVICE_API_KEY="y" * 40,
            VISION_ANALYSIS_MODE="OPENAI_VLM",
            OPENAI_API_KEY=None,
            OPENAI_MODEL="gpt-4o-mini",
            CORS_ORIGINS=["https://example.com"],
        )


def test_gemini_vlm_requires_api_key():
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="development", VISION_ANALYSIS_MODE="GEMINI_VLM", GEMINI_API_KEY="", GEMINI_MODEL="gemini-2.5-flash")


def test_gemini_vlm_requires_model():
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="development", VISION_ANALYSIS_MODE="GEMINI_VLM", GEMINI_API_KEY="gemini-key", GEMINI_MODEL="")


def test_openai_vlm_requires_model_or_legacy_vision_model():
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="development", VISION_ANALYSIS_MODE="OPENAI_VLM", OPENAI_API_KEY="openai-key", OPENAI_MODEL="", VISION_MODEL="")


def test_openai_vlm_accepts_legacy_vision_model():
    settings = Settings(_env_file=None, APP_ENV="development", VISION_ANALYSIS_MODE="OPENAI_VLM", OPENAI_API_KEY="openai-key", VISION_MODEL="gpt-4o-mini")
    assert settings.resolved_openai_model == "gpt-4o-mini"


def test_invalid_vision_mode_fails():
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="development", VISION_ANALYSIS_MODE="INVALID_MODE")


def test_development_allows_example_secrets():
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        JWT_SECRET_KEY="replace-with-secure-secret",
        DEVICE_API_KEY="replace-with-device-key",
    )
    assert settings.JWT_SECRET_KEY == "replace-with-secure-secret"
    assert settings.DEVICE_API_KEY == "replace-with-device-key"


def test_database_url_sqlite_relative_normalized():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="sqlite:///./meal_service.db")
    assert settings.DATABASE_URL == "sqlite:///./meal_service.db"


def test_database_url_sqlite_absolute_supported():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="sqlite:////data/meal_service.db")
    assert settings.DATABASE_URL == "sqlite:////data/meal_service.db"


def test_database_url_postgres_converted():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="postgres://user:password@host/db")
    assert settings.DATABASE_URL == "postgresql+psycopg://user:password@host/db"


def test_database_url_postgresql_converted():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="postgresql://user:password@host/db")
    assert settings.DATABASE_URL == "postgresql+psycopg://user:password@host/db"


def test_database_url_psycopg_preserved():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="postgresql+psycopg://user:password@host/db")
    assert settings.DATABASE_URL == "postgresql+psycopg://user:password@host/db"


def test_database_url_unpooled_normalized():
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="sqlite:///./meal_service.db", DATABASE_URL_UNPOOLED="postgres://user:password@host/db")
    assert settings.DATABASE_URL_UNPOOLED == "postgresql+psycopg://user:password@host/db"


def test_production_blob_with_sqlite_rejected():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="sqlite:///./meal_service.db",
            STORAGE_BACKEND="VERCEL_BLOB",
            BLOB_STORE_ID="store",
            BLOB_READ_WRITE_TOKEN="token",
            JWT_SECRET_KEY="x" * 40,
            DEVICE_API_KEY="y" * 40,
            CORS_ORIGINS=["https://example.com"],
        )


def test_local_storage_settings_success():
    settings = Settings(_env_file=None, APP_ENV="development", STORAGE_BACKEND="LOCAL")
    assert settings.STORAGE_BACKEND == "LOCAL"


def test_vercel_blob_settings_success():
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        STORAGE_BACKEND="VERCEL_BLOB",
        BLOB_STORE_ID="",
        BLOB_READ_WRITE_TOKEN="token",
    )
    assert settings.STORAGE_BACKEND == "VERCEL_BLOB"


def test_vercel_blob_settings_missing_credentials_fail():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            APP_ENV="development",
            STORAGE_BACKEND="VERCEL_BLOB",
            BLOB_STORE_ID="store",
            BLOB_READ_WRITE_TOKEN="",
            VERCEL_OIDC_TOKEN="",
        )


def test_health_ready_success(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "UP"
    assert body["data"]["database"] == "UP"
    assert body["data"]["storage"] == "UP"


def test_health_live_success(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "UP"


def test_health_db_error_returns_503(client, monkeypatch):
    original_execute = Session.execute

    def broken_execute(self, *args, **kwargs):  # noqa: ANN001
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(Session, "execute", broken_execute)
    try:
        response = client.get("/health")
    finally:
        monkeypatch.setattr(Session, "execute", original_execute)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


def test_upload_dir_auto_created(tmp_path, monkeypatch):
    upload_dir = tmp_path / "new-uploads"
    monkeypatch.setattr("app.services.storage.local_storage.settings.UPLOAD_DIR", str(upload_dir))
    ensure_upload_storage_ready()
    assert upload_dir.exists()
    assert (upload_dir / "before").exists()
    assert (upload_dir / "after").exists()


def test_upload_dir_write_failure_raises(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.services.storage.local_storage.settings.UPLOAD_DIR", str(upload_dir))

    def fail_tempfile(*args, **kwargs):  # noqa: ANN001
        raise OSError("no write permission")

    monkeypatch.setattr("tempfile.NamedTemporaryFile", fail_tempfile)
    with pytest.raises(RuntimeError):
        ensure_upload_storage_ready()


def test_dockerfile_does_not_copy_env():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "COPY .env.example ./.env" not in dockerfile


def test_dockerfile_copies_scripts_and_uses_start_sh():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "COPY scripts ./scripts" in dockerfile
    assert 'CMD ["./start.sh"]' in dockerfile


def test_start_sh_runs_migrations_and_uses_port():
    script = Path("start.sh").read_text(encoding="utf-8")
    assert "alembic upgrade head" in script
    assert '${PORT:-8000}' in script
    assert "RUN_MIGRATIONS_ON_START" in script


def test_dockerignore_excludes_env():
    content = Path(".dockerignore").read_text(encoding="utf-8")
    assert ".env" in content


def test_pyproject_has_vercel_entrypoint():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'entrypoint = "app.main:app"' in content


def test_vercel_json_has_max_duration():
    content = Path("vercel.json").read_text(encoding="utf-8")
    assert '"maxDuration": 300' in content
