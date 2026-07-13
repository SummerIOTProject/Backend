from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AppException, ServerException
from app.schemas.meal_analysis import VisionAnalysisResultSchema
from app.utils.enums import AnalysisType


class VisionMenuInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_menu_item_id: int
    menu_id: int
    menu_name: str


class VisionProviderError(AppException):
    pass


class GeminiVisionError(VisionProviderError):
    pass


class OpenAIVisionError(VisionProviderError):
    pass


class VisionProvider(ABC):
    analysis_type: AnalysisType
    provider_name: str
    model_name: str

    @abstractmethod
    async def analyze(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        menu_items: list[VisionMenuInput],
    ) -> VisionAnalysisResultSchema:
        ...


def build_instruction(menu_items: list[VisionMenuInput]) -> str:
    return (
        "당신은 학교 급식 식전·식후 이미지 분석기입니다.\n"
        "첫 번째 이미지는 식전 이미지이고, 두 번째 이미지는 식후 이미지입니다.\n"
        "제공된 메뉴만 분석하며 새로운 메뉴를 추측해 추가하지 마세요.\n"
        "음식의 위치, 남은 양, 용기 상태를 비교해 각 메뉴의 섭취율을 추정하세요.\n"
        "consumed_ratio는 먹은 비율입니다.\n"
        "- 전부 남았으면 0.0\n"
        "- 절반 먹었으면 약 0.5\n"
        "- 전부 먹었으면 1.0\n"
        "가려짐이나 구도 차이가 크면 confidence를 낮추세요.\n"
        "모든 menu item을 정확히 한 번씩 반환하세요.\n"
        "DB에 없는 ID를 만들지 마세요.\n"
        "반드시 JSON schema에 맞춰 응답하세요.\n"
        f"분석 대상 메뉴 목록: {[item.model_dump() for item in menu_items]}"
    )


def build_result_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "meal_menu_item_id": {"type": "integer"},
                        "menu_id": {"type": "integer"},
                        "menu_name": {"type": "string"},
                        "consumed_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "note": {"type": ["string", "null"]},
                    },
                    "required": ["meal_menu_item_id", "menu_id", "menu_name", "consumed_ratio", "confidence", "note"],
                    "additionalProperties": False,
                },
            },
            "analysis_note": {"type": "string"},
        },
        "required": ["items", "analysis_note"],
        "additionalProperties": False,
    }


async def retry_with_backoff(coro_factory, *, retries: int, should_retry, on_retry) -> VisionAnalysisResultSchema:
    max_attempts = max(retries, 0) + 1
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == max_attempts - 1 or not should_retry(exc):
                raise
            await on_retry(exc, attempt + 1)
            await asyncio.sleep((2**attempt) + random.uniform(0, 0.25))
    if last_exc:
        raise last_exc
    raise ServerException(message="VLM API 호출에 실패했습니다.", code="VISION_PROVIDER_UNAVAILABLE", detail="unknown")
