from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AppException, ServerException
from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
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

    @abstractmethod
    async def compare_images(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
    ) -> VisionImageComparisonResultSchema:
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


def build_compare_instruction() -> str:
    return (
        "당신은 학교 급식 식전·식후 이미지 비교 분석기입니다.\n"
        "첫 번째 이미지는 반드시 식전(before) 이미지이고, 두 번째 이미지는 반드시 식후(after) 이미지입니다.\n"
        "두 이미지가 같은 급식판 또는 같은 식사인지 먼저 판단하세요.\n"
        "식전 사진에서 보이는 음식 구성과 식후 사진에서 남은 음식량을 비교하세요.\n"
        "음식별 consumed_ratio는 먹은 비율이며 0.0~1.0 범위만 사용하세요.\n"
        "overall_consumed_ratio는 전체 섭취율입니다.\n"
        "confidence는 전체 판단 신뢰도입니다.\n"
        "같은 식사인지 확실하지 않으면 same_meal을 false로 두고 warnings에 이유를 넣으세요.\n"
        "분석이 불가능하면 analysis_possible을 false로 두고 analysis_impossible_reason을 작성하세요.\n"
        "식후 사진의 음식량이 더 많아 보이면 warnings에 순서 오류 가능성을 명시하세요.\n"
        "음식명을 확신할 수 없으면 추측하지 말고 '알 수 없는 반찬'처럼 일반적으로 표현하세요.\n"
        "Markdown이나 설명문 없이 JSON만 반환하세요."
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


def build_compare_result_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "overall_consumed_ratio": {"type": "number", "minimum": 0, "maximum": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "consumed_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "note": {"type": ["string", "null"]},
                    },
                    "required": ["item_name", "consumed_ratio", "confidence", "note"],
                    "additionalProperties": False,
                },
            },
            "summary": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "analysis_possible": {"type": "boolean"},
            "same_meal": {"type": "boolean"},
            "analysis_impossible_reason": {"type": ["string", "null"]},
        },
        "required": [
            "overall_consumed_ratio",
            "confidence",
            "items",
            "summary",
            "warnings",
            "analysis_possible",
            "same_meal",
            "analysis_impossible_reason",
        ],
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
