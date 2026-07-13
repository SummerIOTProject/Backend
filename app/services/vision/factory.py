from __future__ import annotations

from app.core.config import settings
from app.services.vision.base import VisionProvider
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
