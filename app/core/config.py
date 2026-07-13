from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "smart-meal-api"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./meal_service.db"

    JWT_SECRET_KEY: str = "replace-with-secure-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    DEVICE_API_KEY: str = "replace-with-device-key"

    OPENAI_API_KEY: str | None = None
    VISION_MODEL: str = "gpt-4o-mini"
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

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        self.DATABASE_URL = "sqlite:///./meal_service.db" if self.DATABASE_URL == "sqlite:///./smart_meal.db" else self.DATABASE_URL
        if self.APP_ENV != "development":
            self.DEBUG = False
            if self.JWT_SECRET_KEY == "replace-with-secure-secret":
                raise ValueError("JWT_SECRET_KEY must be changed outside development.")
            if self.DEVICE_API_KEY == "replace-with-device-key":
                raise ValueError("DEVICE_API_KEY must be changed outside development.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
