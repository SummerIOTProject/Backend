from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.repositories.meal_record_repository import MealRecordRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.rfid_repository import RfidRepository
from app.repositories.user_repository import UserRepository
from app.utils.datetime import date_days_ago, today_local
from app.utils.enums import MealRecordStatus


class MealRecordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_record_repository = MealRecordRepository(db)
        self.rfid_repository = RfidRepository(db)
        self.meal_repository = MealRepository(db)
        self.user_repository = UserRepository(db)

    def create_from_rfid(self, *, rfid_uid: str, meal_id: int):
        card = self.rfid_repository.get_active_by_uid(rfid_uid)
        if not card:
            raise NotFoundException(message="RFID 카드를 찾을 수 없습니다.", code="RFID_NOT_FOUND", detail=rfid_uid)
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_id={meal_id}")
        if self.meal_record_repository.get_by_user_and_meal(user_id=card.user_id, meal_id=meal_id):
            raise ConflictException(message="이미 생성된 식사 기록입니다.", code="DUPLICATE_MEAL_RECORD", detail="duplicate meal record")
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
        end_date = today_local()
        start_date = date_days_ago(days - 1)
        records = self.meal_record_repository.list_recent_completed_by_user(user_id=user_id, start_date=start_date, end_date=end_date)
        return start_date, end_date, records

    def mark_before_uploaded(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.BEFORE_IMAGE_UPLOADED)
        self.db.commit()
        return record

    def mark_images_uploaded(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.IMAGES_UPLOADED)
        self.db.commit()
        return record

    def mark_analyzing(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        if record.status == MealRecordStatus.ANALYZING:
            raise ConflictException(message="이미 분석 중입니다.", code="ANALYSIS_ALREADY_RUNNING", detail=f"meal_record_id={meal_record_id}")
        self.meal_record_repository.update_status(record, status=MealRecordStatus.ANALYZING)
        self.db.commit()

    def mark_completed(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.COMPLETED, completed_at=datetime.now(UTC), failure_reason=None)
        self.db.commit()

    def mark_failed(self, meal_record_id: int):
        record = self.get_record(meal_record_id)
        self.meal_record_repository.update_status(record, status=MealRecordStatus.FAILED)
        self.db.commit()

    def list_all(self):
        return self.meal_record_repository.list_all()
