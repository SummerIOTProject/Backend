from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException, UnauthorizedException
from app.repositories.meal_image_repository import MealImageRepository
from app.repositories.meal_item_record_repository import MealItemRecordRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.rfid_repository import RfidRepository
from app.repositories.user_repository import UserRepository
from app.utils.datetime import get_current_date, get_current_utc_datetime, get_recent_start_date
from app.utils.enums import ImageType, MealRecordStatus


class MealRecordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_record_repository = MealRecordRepository(db)
        self.meal_image_repository = MealImageRepository(db)
        self.meal_item_record_repository = MealItemRecordRepository(db)
        self.rfid_repository = RfidRepository(db)
        self.meal_repository = MealRepository(db)
        self.user_repository = UserRepository(db)
        self.recommendation_repository = RecommendationRepository(db)

    def create_from_rfid(self, *, rfid_uid: str, meal_id: int):
        card = self.rfid_repository.get_by_uid(rfid_uid)
        if not card:
            raise NotFoundException(message="RFID 카드를 찾을 수 없습니다.", code="RFID_NOT_FOUND", detail=rfid_uid)
        if not card.is_active:
            raise BadRequestException(message="비활성 RFID 카드입니다.", code="INACTIVE_RFID_CARD", detail=rfid_uid)
        if not card.user.is_active:
            raise UnauthorizedException(message="비활성화된 계정입니다.", code="INACTIVE_USER", detail=f"user_id={card.user_id}")
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_id={meal_id}")
        if meal.school_name != settings.SCHOOL_NAME:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_id={meal_id}")
        if meal.meal_date != get_current_date():
            raise BadRequestException(message="오늘 급식만 기록할 수 있습니다.", code="INVALID_MEAL_DATE", detail=str(meal.meal_date))
        if self.meal_record_repository.get_by_user_and_meal(user_id=card.user_id, meal_id=meal_id):
            raise ConflictException(message="이미 생성된 식사 기록입니다.", code="MEAL_RECORD_ALREADY_EXISTS", detail="duplicate meal record")
        record = self.meal_record_repository.create(user_id=card.user_id, meal_id=meal_id)
        self.db.commit()
        return self.get_record(record.id)

    def get_record(self, meal_record_id: int):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise NotFoundException(message="식사 기록을 찾을 수 없습니다.", code="MEAL_RECORD_NOT_FOUND", detail=f"meal_record_id={meal_record_id}")
        return record

    def assert_owner(self, meal_record_id: int, user_id: int):
        record = self.get_record(meal_record_id)
        if record.user_id != user_id:
            raise ForbiddenException(message="접근 권한이 없습니다.", code="FORBIDDEN_RESOURCE", detail=f"meal_record_id={meal_record_id}")
        return record

    def list_recent(self, user_id: int, days: int):
        days = min(max(days, 1), 30)
        end_date = get_current_date()
        start_date = get_recent_start_date(days)
        records = self.meal_record_repository.list_recent_completed_by_user(user_id=user_id, start_date=start_date, end_date=end_date)
        return start_date, end_date, records

    def recalculate_status_after_image_change(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        status = self._calculate_status_from_db_images(meal_record_id)
        self.meal_record_repository.update_status(record, status=status, completed_at=None, failure_reason=None)
        self.meal_item_record_repository.delete_by_record(meal_record_id)
        self.recommendation_repository.delete_by_user_and_meal(user_id=record.user_id, meal_id=record.meal_id)
        self.db.flush()
        return record

    def mark_analyzing(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        if record.status == MealRecordStatus.ANALYZING:
            raise ConflictException(message="이미 분석 중입니다.", code="ANALYSIS_ALREADY_RUNNING", detail=f"meal_record_id={meal_record_id}")
        self.meal_record_repository.update_status(record, status=MealRecordStatus.ANALYZING)
        self.db.commit()

    def mark_completed(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.COMPLETED, completed_at=get_current_utc_datetime(), failure_reason=None)
        self.db.commit()

    def mark_failed(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.FAILED)
        self.db.commit()

    def list_all(self):
        return self.meal_record_repository.list_all()

    def _calculate_status_from_db_images(self, meal_record_id: int) -> MealRecordStatus:
        has_before = self.meal_image_repository.has_image_type(meal_record_id, ImageType.BEFORE)
        has_after = self.meal_image_repository.has_image_type(meal_record_id, ImageType.AFTER)
        if has_before and has_after:
            return MealRecordStatus.IMAGES_UPLOADED
        if has_before:
            return MealRecordStatus.BEFORE_IMAGE_UPLOADED
        return MealRecordStatus.CREATED
