from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.repositories.meal_record_repository import MealRecordRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.user_repository import UserRepository
from app.schemas.meal_record import MealRecordCreateRequest


class MealRecordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_record_repository = MealRecordRepository(db)
        self.user_repository = UserRepository(db)
        self.meal_repository = MealRepository(db)

    def create_record(self, request: MealRecordCreateRequest):
        user = self.user_repository.get_by_id(request.user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={request.user_id}",
            )
        meal = self.meal_repository.get_by_id(request.meal_id)
        if not meal:
            raise NotFoundException(
                message="식단을 찾을 수 없습니다.",
                code="MEAL_NOT_FOUND",
                detail=f"meal_id={request.meal_id}",
            )
        existing = self.meal_record_repository.get_by_user_and_meal(user_id=request.user_id, meal_id=request.meal_id)
        if existing:
            raise ConflictException(
                message="이미 생성된 식사 기록입니다.",
                code="DUPLICATE_MEAL_RECORD",
                detail=f"user_id={request.user_id}, meal_id={request.meal_id}",
            )
        record = self.meal_record_repository.create(user_id=request.user_id, meal_id=request.meal_id)
        self.db.commit()
        return self.get_record_detail(record.id)

    def get_record_detail(self, meal_record_id: int):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise NotFoundException(
                message="식사 기록을 찾을 수 없습니다.",
                code="MEAL_RECORD_NOT_FOUND",
                detail=f"meal_record_id={meal_record_id}",
            )
        return record

    def list_user_records(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}",
            )
        return self.meal_record_repository.list_by_user(user_id)

    def list_all_records(self):
        return self.meal_record_repository.list_all()

    def assert_record_owner(self, meal_record_id: int, user_id: int):
        record = self.get_record_detail(meal_record_id)
        if record.user_id != user_id:
            raise ForbiddenException(
                message="본인 식사 기록만 조회할 수 있습니다.",
                code="MEAL_RECORD_FORBIDDEN",
                detail=f"meal_record_id={meal_record_id}, user_id={user_id}",
            )
        return record

    def delete_record(self, meal_record_id: int) -> None:
        record = self.get_record_detail(meal_record_id)
        self.meal_record_repository.delete(record)
        self.db.commit()
