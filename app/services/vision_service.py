from __future__ import annotations

from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
from app.services.vision import VisionMenuInput, VisionProvider, build_vision_provider
from app.utils.enums import AnalysisType


class VisionService:
    def __init__(self, provider: VisionProvider | None = None) -> None:
        self.provider = provider or build_vision_provider()

    def current_analysis_type(self) -> AnalysisType:
        return self.provider.analysis_type

    async def analyze(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
        menu_items: list[dict] | list[VisionMenuInput],
    ) -> tuple[AnalysisType, VisionAnalysisResultSchema]:
        normalized_items = [item if isinstance(item, VisionMenuInput) else VisionMenuInput.model_validate(item) for item in menu_items]
        result = await self.provider.analyze(
            before_image=before_image,
            before_mime_type=before_mime_type,
            after_image=after_image,
            after_mime_type=after_mime_type,
            menu_items=normalized_items,
        )
        return self.provider.analysis_type, result

    async def compare_images(
        self,
        *,
        before_image: bytes,
        before_mime_type: str,
        after_image: bytes,
        after_mime_type: str,
    ) -> tuple[AnalysisType, VisionImageComparisonResultSchema]:
        result = await self.provider.compare_images(
            before_image=before_image,
            before_mime_type=before_mime_type,
            after_image=after_image,
            after_mime_type=after_mime_type,
        )
        return self.provider.analysis_type, result
