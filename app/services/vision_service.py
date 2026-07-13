from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, AuthenticationError, BadRequestError, OpenAIError, RateLimitError
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import BadRequestException, ServerException
from app.schemas.meal_analysis import VisionAnalysisResultSchema
from app.utils.enums import AnalysisType
from app.utils.files import file_to_base64

logger = logging.getLogger(__name__)


class VisionService:
    def __init__(self) -> None:
        self.client: AsyncOpenAI | None = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.VISION_TIMEOUT_SECONDS)

    def current_analysis_type(self) -> AnalysisType:
        try:
            return AnalysisType(settings.VISION_ANALYSIS_MODE)
        except ValueError as exc:
            raise BadRequestException(message="지원하지 않는 분석 타입입니다.", code="INVALID_VLM_RESPONSE", detail=settings.VISION_ANALYSIS_MODE) from exc

    async def analyze(
        self,
        *,
        before_path: str,
        before_mime_type: str,
        after_path: str,
        after_mime_type: str,
        menu_items: list[dict],
    ) -> tuple[AnalysisType, VisionAnalysisResultSchema]:
        analysis_type = self.current_analysis_type()
        if analysis_type == AnalysisType.MOCK:
            return analysis_type, self._mock(menu_items)
        if analysis_type == AnalysisType.OPENAI_VLM:
            return analysis_type, await self._openai_vlm(before_path, before_mime_type, after_path, after_mime_type, menu_items)
        raise BadRequestException(message="지원하지 않는 분석 타입입니다.", code="INVALID_VLM_RESPONSE", detail=str(analysis_type))

    def _mock(self, menu_items: list[dict]) -> VisionAnalysisResultSchema:
        items = []
        base_values = [0.95, 0.65, 0.35, 0.05]
        for index, item in enumerate(menu_items):
            items.append(
                {
                    "meal_menu_item_id": item["meal_menu_item_id"],
                    "menu_id": item["menu_id"],
                    "menu_name": item["menu_name"],
                    "consumed_ratio": base_values[index % len(base_values)],
                    "confidence": 0.9,
                    "note": "MOCK 분석 결과",
                }
            )
        return VisionAnalysisResultSchema(items=items)

    async def _openai_vlm(
        self,
        before_path: str,
        before_mime_type: str,
        after_path: str,
        after_mime_type: str,
        menu_items: list[dict],
    ) -> VisionAnalysisResultSchema:
        if not settings.OPENAI_API_KEY or not self.client:
            raise ServerException(message="OpenAI API 키가 필요합니다.", code="OPENAI_API_KEY_MISSING", detail="OPENAI_API_KEY is empty")
        request_id = uuid4().hex
        start_time = time.perf_counter()
        prompt = {
            "role": "user",
            "content": [
                {"type": "input_text", "text": self._build_instruction(menu_items)},
                {"type": "input_image", "image_url": f"data:{before_mime_type};base64,{file_to_base64(before_path)}"},
                {"type": "input_image", "image_url": f"data:{after_mime_type};base64,{file_to_base64(after_path)}"},
            ],
        }
        last_exc: Exception | None = None
        max_attempts = max(settings.VISION_MAX_RETRIES, 0) + 1
        for attempt in range(max_attempts):
            try:
                response = await self.client.responses.create(
                    model=settings.VISION_MODEL,
                    input=[prompt],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "meal_analysis_result",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "meal_menu_item_id": {"type": "integer"},
                                                "menu_id": {"type": "integer"},
                                                "menu_name": {"type": "string"},
                                                "consumed_ratio": {"type": "number"},
                                                "confidence": {"type": "number"},
                                                "note": {"type": ["string", "null"]},
                                            },
                                            "required": ["meal_menu_item_id", "menu_id", "menu_name", "consumed_ratio", "confidence", "note"],
                                            "additionalProperties": False,
                                        },
                                    }
                                },
                                "required": ["items"],
                                "additionalProperties": False,
                            },
                        }
                    },
                )
                output_text = response.output_text
                logger.info(
                    "vlm_success request_id=%s model=%s meal_menu_items=%s attempts=%s elapsed_ms=%s",
                    request_id,
                    settings.VISION_MODEL,
                    len(menu_items),
                    attempt + 1,
                    round((time.perf_counter() - start_time) * 1000, 2),
                )
                return VisionAnalysisResultSchema.model_validate_json(output_text)
            except AuthenticationError as exc:
                logger.error("vlm_auth_error request_id=%s error=%s", request_id, type(exc).__name__)
                raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail="OpenAI authentication error") from exc
            except BadRequestError as exc:
                logger.error("vlm_bad_request request_id=%s error=%s", request_id, type(exc).__name__)
                raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail="bad request") from exc
            except APITimeoutError as exc:
                last_exc = exc
                logger.warning("vlm_timeout request_id=%s model=%s attempt=%s", request_id, settings.VISION_MODEL, attempt + 1)
                if attempt == max_attempts - 1:
                    raise ServerException(message="VLM API 시간 초과입니다.", code="VLM_TIMEOUT", detail="timeout") from exc
                await _async_sleep(2**attempt)
            except (RateLimitError, APIConnectionError) as exc:
                last_exc = exc
                logger.warning("vlm_retryable_error request_id=%s model=%s attempt=%s error=%s", request_id, settings.VISION_MODEL, attempt + 1, type(exc).__name__)
                if attempt == max_attempts - 1:
                    raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail="retryable vlm error") from exc
                await _async_sleep(2**attempt)
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.error("vlm_json_error request_id=%s", request_id)
                raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", detail="json parsing failed") from exc
            except OpenAIError as exc:
                logger.error("vlm_openai_error request_id=%s error=%s", request_id, type(exc).__name__)
                raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail="openai error") from exc
            except Exception as exc:
                logger.error("vlm_unknown_error request_id=%s error=%s", request_id, type(exc).__name__)
                raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail="unexpected vlm error") from exc
        raise ServerException(message="VLM API 호출에 실패했습니다.", code="VLM_API_ERROR", detail=str(last_exc))

    @staticmethod
    def _build_instruction(menu_items: list[dict]) -> str:
        return (
            "당신은 학교 급식 식전·식후 이미지 분석기입니다.\n"
            "입력된 첫 번째 이미지는 식사 전 사진이고, 두 번째 이미지는 식사 후 사진입니다.\n"
            "제공된 오늘 메뉴 목록을 기준으로 각 메뉴가 얼마나 섭취되었는지 추정하세요.\n"
            "규칙:\n"
            "- 메뉴 목록에 없는 음식을 새로 만들지 마세요.\n"
            "- 각 메뉴는 정확히 한 번만 반환하세요.\n"
            "- 모든 메뉴를 누락 없이 반환하세요.\n"
            "- consumed_ratio는 0.0 이상 1.0 이하입니다.\n"
            "- 0.0은 전혀 먹지 않음입니다.\n"
            "- 1.0은 전부 먹음입니다.\n"
            "- 정확한 무게가 아니라 시각적 비율 추정입니다.\n"
            "- 식별이 어려우면 confidence를 낮게 반환하세요.\n"
            "- 음식이 섞였거나 사진 구도가 크게 다르면 note에 기록하세요.\n"
            "- 식판, 수저, 컵, 빈 공간은 음식으로 판단하지 마세요.\n"
            "- 반드시 지정된 JSON schema로만 반환하세요.\n"
            f"오늘 메뉴 목록: {menu_items}"
        )


async def _async_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)
