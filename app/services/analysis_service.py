from datetime import UTC, datetime

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException
from app.repositories.meal_image_repository import MealImageRepository
from app.repositories.meal_item_record_repository import MealItemRecordRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.services.vision_service import VisionService
from app.utils.enums import ConsumptionLevel, ImageType, MealRecordStatus


class AnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_record_repository = MealRecordRepository(db)
        self.image_repository = MealImageRepository(db)
        self.meal_item_record_repository = MealItemRecordRepository(db)
        self.vision_service = VisionService()

    async def analyze(self, meal_record_id: int, *, user_id: int | None = None, allow_completed: bool = False):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise BadRequestException(message="식사 기록을 찾을 수 없습니다.", code="MEAL_RECORD_NOT_FOUND", detail=f"meal_record_id={meal_record_id}")
        if user_id is not None and record.user_id != user_id:
            raise ForbiddenException(message="접근 권한이 없습니다.", code="FORBIDDEN_RESOURCE", detail=f"meal_record_id={meal_record_id}")
        before_image = self.image_repository.get_by_record_and_type(meal_record_id, ImageType.BEFORE)
        after_image = self.image_repository.get_by_record_and_type(meal_record_id, ImageType.AFTER)
        if not before_image:
            raise BadRequestException(message="식전 이미지가 필요합니다.", code="BEFORE_IMAGE_REQUIRED", detail="before image missing")
        if not after_image:
            raise BadRequestException(message="식후 이미지가 필요합니다.", code="AFTER_IMAGE_REQUIRED", detail="after image missing")

        if record.status == MealRecordStatus.ANALYZING:
            raise ConflictException(message="이미 분석 중입니다.", code="ANALYSIS_ALREADY_RUNNING", detail=f"meal_record_id={meal_record_id}")
        if record.status == MealRecordStatus.COMPLETED and not allow_completed:
            existing_items = self.meal_item_record_repository.list_by_record(meal_record_id)
            existing_type = existing_items[0].analysis_type if existing_items else self.vision_service.current_analysis_type()
            return existing_items, existing_type
        if allow_completed and any(item.is_corrected for item in record.item_records):
            raise ConflictException(message="보정된 결과가 있어 재분석할 수 없습니다.", code="CORRECTED_RESULT_EXISTS", detail=f"meal_record_id={meal_record_id}")

        self.meal_record_repository.update_status(record, status=MealRecordStatus.ANALYZING, completed_at=None, failure_reason=None)
        self.db.commit()

        try:
            menu_items = [
                {
                    "meal_menu_item_id": item.id,
                    "menu_id": item.menu_id,
                    "menu_name": item.menu.name,
                }
                for item in record.meal.meal_menu_items
            ]
            analysis_type, result = await self.vision_service.analyze(
                before_path=str(Path(settings.UPLOAD_DIR) / before_image.image_url),
                before_mime_type=before_image.mime_type,
                after_path=str(Path(settings.UPLOAD_DIR) / after_image.image_url),
                after_mime_type=after_image.mime_type,
                menu_items=menu_items,
            )
            self._validate_result(menu_items, result.items)
            if allow_completed:
                self.meal_item_record_repository.delete_by_record(meal_record_id)
            for item in result.items:
                existing = self.meal_item_record_repository.get_by_record_and_meal_menu_item(meal_record_id, item.meal_menu_item_id)
                self.meal_item_record_repository.create_or_update(
                    existing,
                    meal_record_id=meal_record_id,
                    meal_menu_item_id=item.meal_menu_item_id,
                    consumed_ratio=item.consumed_ratio,
                    consumption_level=self._level(item.consumed_ratio),
                    confidence=item.confidence,
                    is_corrected=False,
                    corrected_at=None,
                    corrected_by=None,
                    note=item.note,
                    analysis_type=analysis_type,
                )
            self.meal_record_repository.update_status(
                record,
                status=MealRecordStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                failure_reason=None,
            )
            self.db.commit()
            return self.meal_item_record_repository.list_by_record(meal_record_id), analysis_type
        except Exception as exc:
            self.db.rollback()
            failed_record = self.meal_record_repository.get_by_id(meal_record_id)
            self.meal_record_repository.update_status(
                failed_record,
                status=MealRecordStatus.FAILED,
                completed_at=None,
                failure_reason=self._safe_failure_reason(exc),
            )
            self.db.commit()
            raise

    async def reanalyze(self, meal_record_id: int, *, user_id: int):
        return await self.analyze(meal_record_id, user_id=user_id, allow_completed=True)

    def correct_consumed_ratio(self, meal_item_record_id: int, user_id: int, consumed_ratio: float):
        item_record = self.meal_item_record_repository.get_by_id(meal_item_record_id)
        if not item_record:
            raise BadRequestException(message="분석 항목을 찾을 수 없습니다.", code="MEAL_RECORD_NOT_FOUND", detail=f"meal_item_record_id={meal_item_record_id}")
        if item_record.meal_record.user_id != user_id:
            raise ForbiddenException(message="접근 권한이 없습니다.", code="FORBIDDEN_RESOURCE", detail=f"meal_item_record_id={meal_item_record_id}")
        if not 0.0 <= consumed_ratio <= 1.0:
            raise BadRequestException(message="섭취율 값이 올바르지 않습니다.", code="INVALID_CONSUMED_RATIO", detail=str(consumed_ratio))
        self.meal_item_record_repository.create_or_update(
            item_record,
            meal_record_id=item_record.meal_record_id,
            meal_menu_item_id=item_record.meal_menu_item_id,
            consumed_ratio=consumed_ratio,
            consumption_level=self._level(consumed_ratio),
            confidence=None,
            is_corrected=True,
            corrected_at=datetime.now(UTC),
            corrected_by=user_id,
            note=item_record.note,
            analysis_type=item_record.analysis_type,
        )
        self.db.commit()
        return self.meal_item_record_repository.get_by_id(meal_item_record_id)

    @staticmethod
    def _validate_result(menu_items: list[dict], items: list) -> None:
        expected_ids = {item["meal_menu_item_id"] for item in menu_items}
        expected_pairs = {item["meal_menu_item_id"]: item for item in menu_items}
        actual_ids = [item.meal_menu_item_id for item in items]
        if len(actual_ids) != len(expected_ids):
            raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="VLM_MENU_MISSING", detail="menu count mismatch")
        if not actual_ids:
            raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", detail="items is empty")
        if len(set(actual_ids)) != len(actual_ids):
            raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="VLM_DUPLICATE_MENU", detail="duplicate meal_menu_item_id")
        if set(actual_ids) != expected_ids:
            raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="VLM_MENU_MISSING", detail="missing menu item")
        for item in items:
            source = expected_pairs[item.meal_menu_item_id]
            if item.menu_id != source["menu_id"]:
                raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", detail="menu_id mismatch")
            if not 0.0 <= item.consumed_ratio <= 1.0:
                raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="VLM_INVALID_RATIO", detail="consumed_ratio out of range")
            if not 0.0 <= item.confidence <= 1.0:
                raise BadRequestException(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", detail="confidence out of range")

    @staticmethod
    def _level(ratio: float) -> ConsumptionLevel:
        if ratio < 0.10:
            return ConsumptionLevel.NONE
        if ratio < 0.40:
            return ConsumptionLevel.LITTLE
        if ratio < 0.70:
            return ConsumptionLevel.HALF
        if ratio < 0.95:
            return ConsumptionLevel.MOST
        return ConsumptionLevel.ALL

    @staticmethod
    def _safe_failure_reason(exc: Exception) -> str:
        detail = str(exc)
        if len(detail) > 200:
            detail = detail[:200]
        return f"{type(exc).__name__}: {detail}"
