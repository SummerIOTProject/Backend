from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.image_repository import ImageRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.schemas.meal_analysis import MealAnalyzeRequest, MealReanalyzeRequest
from app.services.vision_service import VisionService
from app.utils.enums import ConsumptionLevel, ImageType, MealRecordStatus


class AnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_record_repository = MealRecordRepository(db)
        self.image_repository = ImageRepository(db)
        self.analysis_repository = AnalysisRepository(db)
        self.vision_service = VisionService()

    def analyze(self, meal_record_id: int, request: MealAnalyzeRequest):
        return self._run_analysis(meal_record_id=meal_record_id, analysis_type=request.analysis_type, replace_existing=False)

    def reanalyze(self, meal_record_id: int, request: MealReanalyzeRequest):
        return self._run_analysis(meal_record_id=meal_record_id, analysis_type=request.analysis_type, replace_existing=True)

    def get_analysis(self, meal_record_id: int):
        record = self._get_record_or_raise(meal_record_id)
        items = self.analysis_repository.list_by_record(meal_record_id)
        return {
            "meal_record_id": record.id,
            "analysis_note": "저장된 분석 결과입니다.",
            "items": items,
        }

    def _run_analysis(self, *, meal_record_id: int, analysis_type, replace_existing: bool):
        record = self._get_record_or_raise(meal_record_id)
        before_image = self.image_repository.get_by_record_and_type(meal_record_id, ImageType.BEFORE)
        after_image = self.image_repository.get_by_record_and_type(meal_record_id, ImageType.AFTER)
        if not before_image:
            raise BadRequestException(
                message="식전 이미지가 필요합니다.",
                code="BEFORE_IMAGE_REQUIRED",
                detail="분석 전 식전 이미지를 업로드하세요.",
            )
        if not after_image:
            raise BadRequestException(
                message="식후 이미지가 필요합니다.",
                code="AFTER_IMAGE_REQUIRED",
                detail="분석 전 식후 이미지를 업로드하세요.",
            )
        try:
            self.meal_record_repository.update_status(record, status=MealRecordStatus.ANALYZING, completed_at=None, failure_reason=None)
            self.db.commit()
            menu_items = list(record.meal.menu_items)
            result = self.vision_service.analyze(analysis_type=analysis_type, menu_items=menu_items)
            if replace_existing:
                self.analysis_repository.delete_by_record(meal_record_id)
            menu_item_ids = {item.id for item in menu_items}
            for item in result.items:
                if item.meal_menu_item_id not in menu_item_ids:
                    raise BadRequestException(
                        message="분석 결과에 유효하지 않은 메뉴가 포함되었습니다.",
                        code="ANALYSIS_FAILED",
                        detail=f"meal_menu_item_id={item.meal_menu_item_id}",
                    )
                if not 0 <= item.consumed_ratio <= 1:
                    raise BadRequestException(
                        message="섭취 비율이 유효하지 않습니다.",
                        code="ANALYSIS_FAILED",
                        detail=f"consumed_ratio={item.consumed_ratio}",
                    )
                existing = None if replace_existing else self.analysis_repository.get_by_record_and_menu_item(
                    meal_record_id, item.meal_menu_item_id
                )
                self.analysis_repository.create_or_update(
                    existing=existing,
                    meal_record_id=meal_record_id,
                    meal_menu_item_id=item.meal_menu_item_id,
                    consumed_ratio=item.consumed_ratio,
                    consumption_level=self._to_consumption_level(item.consumed_ratio),
                    confidence=item.confidence,
                    note=item.note,
                )
            self.meal_record_repository.update_status(
                record,
                status=MealRecordStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                failure_reason=None,
            )
            self.db.commit()
            return {
                "meal_record_id": record.id,
                "analysis_note": result.analysis_note,
                "items": self.analysis_repository.list_by_record(meal_record_id),
            }
        except Exception as exc:
            self.db.rollback()
            record = self._get_record_or_raise(meal_record_id)
            self.meal_record_repository.update_status(
                record,
                status=MealRecordStatus.FAILED,
                completed_at=None,
                failure_reason=str(exc),
            )
            self.db.commit()
            if isinstance(exc, BadRequestException):
                raise exc
            raise BadRequestException(
                message="분석 처리에 실패했습니다.",
                code="ANALYSIS_FAILED",
                detail=str(exc),
            ) from exc

    def _get_record_or_raise(self, meal_record_id: int):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise BadRequestException(
                message="식사 기록을 찾을 수 없습니다.",
                code="MEAL_RECORD_NOT_FOUND",
                detail=f"meal_record_id={meal_record_id}",
            )
        return record

    @staticmethod
    def _to_consumption_level(ratio: float) -> ConsumptionLevel:
        if ratio < 0.1:
            return ConsumptionLevel.NONE
        if ratio < 0.4:
            return ConsumptionLevel.LITTLE
        if ratio < 0.7:
            return ConsumptionLevel.HALF
        if ratio < 0.95:
            return ConsumptionLevel.MOST
        return ConsumptionLevel.ALL
