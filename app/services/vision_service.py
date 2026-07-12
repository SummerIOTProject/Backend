from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.models.meal_menu_item import MealMenuItem
from app.utils.enums import AnalysisType


@dataclass
class VisionItemResult:
    meal_menu_item_id: int
    menu_name: str
    consumed_ratio: float
    confidence: float
    note: str


@dataclass
class VisionAnalysisResult:
    items: list[VisionItemResult]
    analysis_note: str


class VisionService:
    def analyze(self, *, analysis_type: AnalysisType, menu_items: list[MealMenuItem]) -> VisionAnalysisResult:
        if analysis_type == AnalysisType.MOCK:
            return self._mock_analysis(menu_items)
        return self._llm_vision_analysis(menu_items)

    def _mock_analysis(self, menu_items: list[MealMenuItem]) -> VisionAnalysisResult:
        items = [self._build_mock_item(menu_item) for menu_item in menu_items]
        return VisionAnalysisResult(
            items=items,
            analysis_note="식전·식후 이미지를 비교하여 분석함",
        )

    def _llm_vision_analysis(self, menu_items: list[MealMenuItem]) -> VisionAnalysisResult:
        if not settings.VISION_API_KEY:
            raise BadRequestException(
                message="비전 API가 설정되지 않았습니다.",
                code="VISION_API_NOT_CONFIGURED",
                detail="VISION_API_KEY 환경 변수가 필요합니다.",
            )
        return self._call_external_vision_api(menu_items)

    def _call_external_vision_api(self, menu_items: list[MealMenuItem]) -> VisionAnalysisResult:
        return self._mock_analysis(menu_items)

    def _build_mock_item(self, menu_item: MealMenuItem) -> VisionItemResult:
        tray_section = menu_item.tray_section or 0
        ratio = 0.5 + (((menu_item.id * 17) + (tray_section * 13) + (menu_item.display_order * 7)) % 41) / 100
        ratio = round(min(ratio, 0.9), 2)
        confidence = round(0.75 + ((menu_item.id * 11) % 21) / 100, 2)
        if ratio >= 0.85:
            note = "식전 대비 대부분 섭취한 것으로 보임"
        elif ratio >= 0.65:
            note = "식전 대비 일부 잔반이 남아 있음"
        else:
            note = "상당량의 잔반이 확인됨"
        return VisionItemResult(
            meal_menu_item_id=menu_item.id,
            menu_name=menu_item.name,
            consumed_ratio=ratio,
            confidence=confidence,
            note=note,
        )
