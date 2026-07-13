from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "smart-meal-api"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./meal_service.db"
    SCHOOL_NAME: str = "국민대학교"
    APP_TIMEZONE: str = "Asia/Seoul"

    JWT_SECRET_KEY: str = "replace-with-secure-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    DEVICE_API_KEY: str = "replace-with-device-key"
    PORT: int = 8000
    RUN_MIGRATIONS_ON_START: bool = True

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None
    VISION_MODEL: str | None = None
    VISION_ANALYSIS_MODE: str = "MOCK"
    VISION_TIMEOUT_SECONDS: int = 60
    VISION_MAX_RETRIES: int = 2

    UPLOAD_DIR: str = "uploads"
    MAX_IMAGE_SIZE_MB: int = 10
    ANALYSIS_IMAGE_MAX_DIMENSION: int = 2048
    ANALYSIS_IMAGE_JPEG_QUALITY: int = 85
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.APP_TIMEZONE)

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def resolved_openai_model(self) -> str | None:
        return self.OPENAI_MODEL or self.VISION_MODEL

    @staticmethod
    def normalize_database_url(value: str) -> str:
        if value == "sqlite:///./smart_meal.db":
            return "sqlite:///./meal_service.db"
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]
        if value.startswith("postgresql://") and not value.startswith("postgresql+psycopg://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        self.DATABASE_URL = self.normalize_database_url(self.DATABASE_URL)
        allowed_modes = {"MOCK", "GEMINI_VLM", "OPENAI_VLM"}
        if self.VISION_ANALYSIS_MODE not in allowed_modes:
            raise ValueError("VISION_ANALYSIS_MODE must be one of MOCK, GEMINI_VLM, OPENAI_VLM.")
        if self.VISION_ANALYSIS_MODE == "GEMINI_VLM":
            if not self.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is required when VISION_ANALYSIS_MODE=GEMINI_VLM.")
            if not self.GEMINI_MODEL:
                raise ValueError("GEMINI_MODEL is required when VISION_ANALYSIS_MODE=GEMINI_VLM.")
        if self.VISION_ANALYSIS_MODE == "OPENAI_VLM":
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when VISION_ANALYSIS_MODE=OPENAI_VLM.")
            if not self.resolved_openai_model:
                raise ValueError("OPENAI_MODEL or legacy VISION_MODEL is required when VISION_ANALYSIS_MODE=OPENAI_VLM.")
        if self.APP_ENV != "development":
            self.DEBUG = False
            if self.JWT_SECRET_KEY == "replace-with-secure-secret":
                raise ValueError("JWT_SECRET_KEY must be changed outside development.")
            if self.DEVICE_API_KEY == "replace-with-device-key":
                raise ValueError("DEVICE_API_KEY must be changed outside development.")
            if self.JWT_SECRET_KEY == self.DEVICE_API_KEY:
                raise ValueError("JWT_SECRET_KEY and DEVICE_API_KEY must be different.")
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters outside development.")
            if len(self.DEVICE_API_KEY) < 32:
                raise ValueError("DEVICE_API_KEY must be at least 32 characters outside development.")
            if self.CORS_ORIGINS and all(("localhost" in origin or "127.0.0.1" in origin) for origin in self.CORS_ORIGINS):
                raise ValueError("CORS_ORIGINS must include a non-localhost origin outside development.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
