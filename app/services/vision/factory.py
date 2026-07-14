from __future__ import annotations

from app.core.config import settings
from app.services.vision.base import OpenAIVisionError, VisionProvider
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
            detail="OPENAI_VISION_MODEL missing",
        )
    return OpenAIVisionProvider(model_name=settings.resolved_compare_openai_model)
