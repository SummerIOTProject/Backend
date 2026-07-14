from __future__ import annotations

import base64
import json
import logging
import time
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
from app.services.vision.base import (
    OpenAIVisionError,
    VisionMenuInput,
    VisionProvider,
    build_compare_instruction,
    build_compare_result_schema,
    build_instruction,
    build_result_schema,
    retry_with_backoff,
)
from app.utils.enums import AnalysisType

logger = logging.getLogger(__name__)


class OpenAIVisionProvider(VisionProvider):
    analysis_type = AnalysisType.OPENAI_VLM
    provider_name = "openai"
    _client_cache: dict[tuple[str, str], object] = {}

    def __init__(self, *, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.resolved_openai_model or ""
        cache_key = (settings.OPENAI_API_KEY or "", self.model_name)
        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = self._create_client()
        self.client = self._client_cache[cache_key]

    def _create_client(self):
        from openai import AsyncOpenAI

        if not settings.OPENAI_API_KEY:
            raise OpenAIVisionError(message="VLM 설정 오류입니다.", code="VISION_CONFIGURATION_ERROR", status_code=500, detail="OPENAI_API_KEY missing")
        if not self.model_name:
            raise OpenAIVisionError(message="VLM 설정 오류입니다.", code="VISION_CONFIGURATION_ERROR", status_code=500, detail="OPENAI_MODEL missing")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.VISION_TIMEOUT_SECONDS)

    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

        if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)):
            return True
        if isinstance(exc, APIStatusError):
            status_code = getattr(exc, "status_code", None)
            return status_code is not None and 500 <= status_code <= 599
        return False

    def _map_error(self, exc: Exception) -> OpenAIVisionError:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, BadRequestError, OpenAIError, PermissionDeniedError, RateLimitError

        if isinstance(exc, AuthenticationError):
            return OpenAIVisionError(message="VLM 인증에 실패했습니다.", code="VISION_AUTHENTICATION_FAILED", status_code=401, detail="openai authentication failed")
        if isinstance(exc, PermissionDeniedError):
            return OpenAIVisionError(message="VLM 권한이 없습니다.", code="VISION_PERMISSION_DENIED", status_code=403, detail="openai permission denied")
        if isinstance(exc, BadRequestError):
            return OpenAIVisionError(message="VLM 요청 형식이 올바르지 않습니다.", code="VISION_REQUEST_INVALID", status_code=400, detail="openai bad request")
        if isinstance(exc, APITimeoutError):
            return OpenAIVisionError(message="VLM 요청 시간이 초과되었습니다.", code="VISION_TIMEOUT", status_code=503, detail="openai timeout")
        if isinstance(exc, RateLimitError):
            return OpenAIVisionError(message="VLM 요청 한도를 초과했습니다.", code="VISION_QUOTA_EXCEEDED", status_code=503, detail="openai rate limit")
        if isinstance(exc, APIConnectionError):
            return OpenAIVisionError(message="VLM 공급자에 연결할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail="openai connection error")
        if isinstance(exc, APIStatusError):
            status_code = getattr(exc, "status_code", None)
            if status_code is not None and 500 <= status_code <= 599:
                return OpenAIVisionError(message="VLM 공급자를 사용할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail=f"openai server status={status_code}")
            return OpenAIVisionError(message="VLM 요청에 실패했습니다.", code="VISION_REQUEST_INVALID", status_code=400, detail=f"openai status={status_code}")
        if isinstance(exc, (json.JSONDecodeError, ValidationError)):
            return OpenAIVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="invalid structured response")
        if isinstance(exc, OpenAIError):
            return OpenAIVisionError(message="VLM 공급자를 사용할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail="openai error")
        return OpenAIVisionError(message="VLM 공급자를 사용할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail=type(exc).__name__)

    async def analyze(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        menu_items: list[VisionMenuInput],
    ) -> VisionAnalysisResultSchema:
        prompt = {
            "role": "user",
            "content": [
                {"type": "input_text", "text": build_instruction(menu_items)},
                {"type": "input_image", "image_url": f"data:{before_mime_type};base64,{self._image_to_base64(before_image)}"},
                {"type": "input_image", "image_url": f"data:{after_mime_type};base64,{self._image_to_base64(after_image)}"},
            ],
        }
        return await self._run_structured_request(
            prompt=prompt,
            schema_name="meal_analysis_result",
            schema=build_result_schema(),
            parser=VisionAnalysisResultSchema.model_validate_json,
            item_count=len(menu_items),
        )

    async def compare_images(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
    ) -> VisionImageComparisonResultSchema:
        prompt = {
            "role": "user",
            "content": [
                {"type": "input_text", "text": build_compare_instruction()},
                {"type": "input_image", "image_url": f"data:{before_mime_type};base64,{self._image_to_base64(before_image)}"},
                {"type": "input_image", "image_url": f"data:{after_mime_type};base64,{self._image_to_base64(after_image)}"},
            ],
        }
        return await self._run_structured_request(
            prompt=prompt,
            schema_name="image_comparison_result",
            schema=build_compare_result_schema(),
            parser=VisionImageComparisonResultSchema.model_validate_json,
            item_count=0,
            retry_parse_once=True,
        )

    async def _run_structured_request(self, *, prompt: dict, schema_name: str, schema: dict, parser, item_count: int, retry_parse_once: bool = False):
        request_id = uuid4().hex
        start_time = time.perf_counter()
        try:
            async def _call():
                attempts = 2 if retry_parse_once else 1
                last_exc = None
                for _ in range(attempts):
                    response = await self.client.responses.create(
                        model=self.model_name,
                        input=[prompt],
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": schema_name,
                                "schema": schema,
                                "strict": True,
                            }
                        },
                    )
                    try:
                        return parser(response.output_text)
                    except (json.JSONDecodeError, ValidationError) as exc:
                        last_exc = exc
                if last_exc is not None:
                    raise last_exc
                raise OpenAIVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="empty response")

            async def _on_retry(exc: Exception, attempt: int):
                logger.warning("vlm_retry provider=%s request_id=%s model=%s attempt=%s error=%s", self.provider_name, request_id, self.model_name, attempt, type(exc).__name__)

            result = await retry_with_backoff(_call, retries=settings.VISION_MAX_RETRIES, should_retry=self._should_retry, on_retry=_on_retry)
            logger.info(
                "vlm_success provider=%s request_id=%s model=%s meal_menu_items=%s elapsed_ms=%s",
                self.provider_name,
                request_id,
                self.model_name,
                item_count,
                round((time.perf_counter() - start_time) * 1000, 2),
            )
            return result
        except OpenAIVisionError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

    @staticmethod
    def _image_to_base64(image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("ascii")
