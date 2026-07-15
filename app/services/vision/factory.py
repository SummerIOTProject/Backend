from __future__ import annotations

from app.core.config import settings
from app.services.vision.base import GeminiVisionError, OpenAIVisionError, VisionProvider, VisionProviderError
from app.services.vision.gemini_provider import GeminiVisionProvider
from app.services.vision.mock_provider import MockVisionProvider
from app.services.vision.openai_provider import OpenAIVisionProvider
from app.utils.enums import AnalysisType


def build_vision_provider() -> VisionProvider:
    analysis_type = AnalysisType(settings.VISION_ANALYSIS_MODE)
    if analysis_type == AnalysisType.MOCK:
        return MockVisionProvider()
    if analysis_type == AnalysisType.GEMINI_VLM:
        return GeminiVisionProvider()
    if analysis_type == AnalysisType.OPENAI_VLM:
        return OpenAIVisionProvider()
    raise ValueError(f"Unsupported vision analysis mode: {settings.VISION_ANALYSIS_MODE}")


def build_compare_vision_provider() -> VisionProvider:
    try:
        analysis_type = AnalysisType(settings.VISION_ANALYSIS_MODE)
    except ValueError as exc:
        raise VisionProviderError(
            message="지원하지 않는 VLM 분석 모드입니다.",
            code="VLM_MODE_NOT_SUPPORTED",
            status_code=500,
            detail=f"VISION_ANALYSIS_MODE={settings.VISION_ANALYSIS_MODE}",
        ) from exc

    if analysis_type == AnalysisType.GEMINI_VLM:
        if not settings.GEMINI_API_KEY:
            raise GeminiVisionError(
                message="VLM API 키가 설정되지 않았습니다.",
                code="VLM_API_KEY_NOT_CONFIGURED",
                status_code=500,
                detail="GEMINI_API_KEY missing",
            )
        if not settings.GEMINI_MODEL:
            raise GeminiVisionError(
                message="VLM 모델이 설정되지 않았습니다.",
                code="VLM_MODEL_NOT_CONFIGURED",
                status_code=500,
                detail="GEMINI_MODEL missing",
            )
        return GeminiVisionProvider()

    if analysis_type == AnalysisType.OPENAI_VLM:
        if not settings.OPENAI_API_KEY:
            raise OpenAIVisionError(
                message="VLM API 키가 설정되지 않았습니다.",
                code="VLM_API_KEY_NOT_CONFIGURED",
                status_code=500,
                detail="OPENAI_API_KEY missing",
            )
        if not settings.resolved_compare_openai_model:
            raise OpenAIVisionError(
                message="VLM 모델이 설정되지 않았습니다.",
                code="VLM_MODEL_NOT_CONFIGURED",
                status_code=500,
                detail="OPENAI_VISION_MODEL, OPENAI_MODEL, or VISION_MODEL missing",
            )
        return OpenAIVisionProvider(model_name=settings.resolved_compare_openai_model)

    raise VisionProviderError(
        message="이미지 직접 비교에서 지원하지 않는 VLM 분석 모드입니다.",
        code="VLM_MODE_NOT_SUPPORTED",
        status_code=500,
        detail=f"VISION_ANALYSIS_MODE={settings.VISION_ANALYSIS_MODE}",
    )
