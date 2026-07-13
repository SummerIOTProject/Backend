from __future__ import annotations

from app.schemas.meal_analysis import VisionAnalysisResultSchema
from app.services.vision.base import VisionMenuInput, VisionProvider
from app.utils.enums import AnalysisType


class MockVisionProvider(VisionProvider):
    analysis_type = AnalysisType.MOCK
    provider_name = "mock"
    model_name = "mock"

    async def analyze(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        menu_items: list[VisionMenuInput],
    ) -> VisionAnalysisResultSchema:
        items = []
        base_values = [0.95, 0.65, 0.35, 0.05]
        for index, item in enumerate(menu_items):
            items.append(
                {
                    "meal_menu_item_id": item.meal_menu_item_id,
                    "menu_id": item.menu_id,
                    "menu_name": item.menu_name,
                    "consumed_ratio": base_values[index % len(base_values)],
                    "confidence": 0.9,
                    "note": "MOCK 분석 결과",
                }
            )
        return VisionAnalysisResultSchema(items=items, analysis_note="MOCK 식전·식후 이미지 비교 결과")
