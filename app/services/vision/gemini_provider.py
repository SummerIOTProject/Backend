from __future__ import annotations

import asyncio
import json
import logging
import time
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
from app.services.vision.base import (
    GeminiVisionError,
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


class GeminiVisionProvider(VisionProvider):
    analysis_type = AnalysisType.GEMINI_VLM
    provider_name = "gemini"
    _client_cache: dict[tuple[str, str], object] = {}

    def __init__(self) -> None:
        self.model_name = settings.GEMINI_MODEL or ""
        self.timeout_seconds = settings.VISION_TIMEOUT_SECONDS
        cache_key = (settings.GEMINI_API_KEY or "", self.model_name)
        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = self._create_client()
        self.client = self._client_cache[cache_key]

    @staticmethod
    def _create_client():
        if not settings.GEMINI_API_KEY:
            raise GeminiVisionError(message="VLM API 키가 설정되지 않았습니다.", code="VLM_API_KEY_NOT_CONFIGURED", status_code=500, detail="GEMINI_API_KEY missing")
        if not settings.GEMINI_MODEL:
            raise GeminiVisionError(message="VLM 모델이 설정되지 않았습니다.", code="VLM_MODEL_NOT_CONFIGURED", status_code=500, detail="GEMINI_MODEL missing")
        from google import genai

        return genai.Client(api_key=settings.GEMINI_API_KEY)

    @staticmethod
    def _get_status_code(exc: Exception) -> int | None:
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        return None

    @classmethod
    def _should_retry(cls, exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
            return True
        status_code = cls._get_status_code(exc)
        if status_code in {408, 429, 500, 502, 503, 504}:
            return True
        name = type(exc).__name__.lower()
        detail = str(exc).lower()
        if status_code is None and ("timeout" in name or "timeout" in detail):
            return True
        if status_code is None and ("connection" in name or "connection" in detail):
            return True
        if status_code is None and ("quota" in detail or "rate limit" in detail):
            return True
        return False

    @classmethod
    def _error_summary(cls, exc: Exception) -> str:
        status_code = cls._get_status_code(exc)
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or status_code == 408:
            return "request timed out"
        if status_code == 400:
            return "request invalid"
        if status_code == 401:
            return "authentication failed"
        if status_code == 403:
            return "permission denied"
        if status_code == 404:
            return "model not found"
        if status_code == 429:
            return "quota exceeded"
        if status_code in {500, 502, 503, 504}:
            return "provider unavailable"
        if isinstance(exc, ConnectionError):
            return "provider unavailable"
        detail = str(exc).lower()
        if "quota" in detail or "rate limit" in detail:
            return "quota exceeded"
        if "timeout" in detail:
            return "request timed out"
        if "connection" in detail:
            return "provider unavailable"
        return "provider error"

    def _map_error(self, exc: Exception) -> GeminiVisionError:
        if isinstance(exc, (json.JSONDecodeError, ValidationError)):
            return GeminiVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="invalid structured response")
        status_code = self._get_status_code(exc)
        detail = str(exc).lower()
        summary = self._error_summary(exc)
        if status_code == 400:
            return GeminiVisionError(message="VLM 요청 형식이 올바르지 않습니다.", code="VISION_REQUEST_INVALID", status_code=400, detail=summary)
        if status_code == 401:
            return GeminiVisionError(message="VLM 인증에 실패했습니다.", code="VISION_AUTHENTICATION_FAILED", status_code=502, detail=summary)
        if status_code == 403:
            return GeminiVisionError(message="VLM 권한이 없습니다.", code="VISION_PERMISSION_DENIED", status_code=403, detail=summary)
        if status_code == 404:
            return GeminiVisionError(message="VLM 요청 형식이 올바르지 않습니다.", code="VISION_REQUEST_INVALID", status_code=400, detail=summary)
        if status_code == 429 or "quota" in detail or "rate limit" in detail:
            return GeminiVisionError(message="VLM 요청 한도를 초과했습니다.", code="VISION_QUOTA_EXCEEDED", status_code=503, detail=summary)
        if status_code in {500, 502, 503, 504}:
            return GeminiVisionError(message="VLM 공급자를 사용할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail=summary)
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or status_code == 408 or "timeout" in type(exc).__name__.lower() or "timeout" in detail:
            return GeminiVisionError(message="VLM 요청 시간이 초과되었습니다.", code="VISION_TIMEOUT", status_code=503, detail=summary)
        if isinstance(exc, ConnectionError) or "connection" in type(exc).__name__.lower() or "connection" in detail:
            return GeminiVisionError(message="VLM 공급자에 연결할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail=summary)
        return GeminiVisionError(message="VLM 공급자를 사용할 수 없습니다.", code="VISION_PROVIDER_UNAVAILABLE", status_code=503, detail=summary)

    async def analyze(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        menu_items: list[VisionMenuInput],
    ) -> VisionAnalysisResultSchema:
        return await self._run_structured_analysis(
            before_image=before_image,
            before_mime_type=before_mime_type,
            after_image=after_image,
            after_mime_type=after_mime_type,
            prompt_text=build_instruction(menu_items),
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
        return await self._run_structured_analysis(
            before_image=before_image,
            before_mime_type=before_mime_type,
            after_image=after_image,
            after_mime_type=after_mime_type,
            prompt_text=build_compare_instruction(),
            schema=build_compare_result_schema(),
            parser=VisionImageComparisonResultSchema.model_validate_json,
            item_count=0,
            retry_parse_once=True,
        )

    async def _run_structured_analysis(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        prompt_text: str,
        schema: dict,
        parser,
        item_count: int,
        retry_parse_once: bool = False,
    ):
        request_id = uuid4().hex
        start_time = time.perf_counter()
        try:
            async def _call():
                attempts = 2 if retry_parse_once else 1
                last_exc = None
                for _ in range(attempts):
                    response = await asyncio.wait_for(
                        self._generate_content(
                            before_image=before_image,
                            before_mime_type=before_mime_type,
                            after_image=after_image,
                            after_mime_type=after_mime_type,
                            prompt_text=prompt_text,
                            schema=schema,
                        ),
                        timeout=getattr(self, "timeout_seconds", settings.VISION_TIMEOUT_SECONDS),
                    )
                    try:
                        return self._parse_response(response, parser=parser)
                    except (json.JSONDecodeError, ValidationError) as exc:
                        last_exc = exc
                if last_exc is not None:
                    raise last_exc
                raise GeminiVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="empty response")

            async def _on_retry(exc: Exception, attempt: int):
                logger.warning(
                    "vlm_retry provider=%s request_id=%s model=%s attempt=%s status_code=%s error=%s",
                    self.provider_name,
                    request_id,
                    self.model_name,
                    attempt,
                    self._get_status_code(exc),
                    self._error_summary(exc),
                )

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
        except GeminiVisionError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

    async def _generate_content(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        prompt_text: str,
        schema: dict,
    ):
        from google.genai import types

        before_part = types.Part.from_bytes(data=before_image, mime_type=before_mime_type)
        after_part = types.Part.from_bytes(data=after_image, mime_type=after_mime_type)
        instruction_part = types.Part.from_text(text=prompt_text)
        contents = [
            types.Content(
                role="user",
                parts=[
                    before_part,
                    after_part,
                    instruction_part,
                ],
            )
        ]
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,
        )
        return await self.client.aio.models.generate_content(model=self.model_name, contents=contents, config=config)

    @staticmethod
    def _parse_response(response, *, parser):
        output_text = getattr(response, "text", None)
        if not output_text:
            output_text = getattr(response, "output_text", None)
        if not output_text:
            raise GeminiVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="empty structured response")
        return parser(output_text)
