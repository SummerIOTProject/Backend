from __future__ import annotations

from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
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

    async def compare_images(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
    ) -> VisionImageComparisonResultSchema:
        return VisionImageComparisonResultSchema(
            same_meal=True,
            overall_consumed_ratio=0.72,
            confidence=0.81,
            items=[
                {
                    "item_name": "밥",
                    "consumed_ratio": 0.85,
                    "confidence": 0.88,
                    "before_description": "밥 칸이 대부분 채워져 있습니다.",
                    "after_description": "밥이 소량 남아 있습니다.",
                    "note": "소량만 남아 있습니다.",
                },
                {
                    "item_name": "육류 반찬",
                    "consumed_ratio": 0.65,
                    "confidence": 0.74,
                    "before_description": "육류 반찬이 한 칸에 담겨 있습니다.",
                    "after_description": "일부 반찬이 남아 있습니다.",
                    "note": "일부가 남아 있습니다.",
                },
            ],
            summary="밥은 대부분 섭취했고 일부 반찬이 남았습니다.",
            warnings=["사진 촬영 각도가 달라 정확도가 낮아질 수 있습니다."],
            analysis_possible=True,
            analysis_impossible_reason=None,
        )
