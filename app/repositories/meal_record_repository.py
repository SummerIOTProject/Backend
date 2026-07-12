from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.meal import Meal
from app.models.meal_analysis import MealAnalysis
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord
from app.models.user import User
from app.utils.enums import MealRecordStatus


class MealRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: int, meal_id: int) -> MealRecord:
        record = MealRecord(user_id=user_id, meal_id=meal_id, status=MealRecordStatus.CREATED)
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_id(self, meal_record_id: int) -> MealRecord | None:
        stmt = (
            select(MealRecord)
            .options(
                joinedload(MealRecord.user),
                joinedload(MealRecord.meal).joinedload(Meal.menu_items),
                joinedload(MealRecord.images),
                joinedload(MealRecord.analyses).joinedload(MealAnalysis.meal_menu_item),
            )
            .where(MealRecord.id == meal_record_id)
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_user_and_meal(self, *, user_id: int, meal_id: int) -> MealRecord | None:
        stmt = select(MealRecord).where(MealRecord.user_id == user_id, MealRecord.meal_id == meal_id)
        return self.db.scalar(stmt)

    def list_by_user(self, user_id: int) -> list[MealRecord]:
        stmt = (
            select(MealRecord)
            .options(joinedload(MealRecord.meal), joinedload(MealRecord.images), joinedload(MealRecord.analyses))
            .where(MealRecord.user_id == user_id)
            .order_by(MealRecord.started_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_all(self) -> list[MealRecord]:
        stmt = (
            select(MealRecord)
            .options(joinedload(MealRecord.user), joinedload(MealRecord.meal))
            .order_by(MealRecord.started_at.desc(), MealRecord.id.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def update_status(
        self,
        record: MealRecord,
        *,
        status: MealRecordStatus,
        completed_at=None,
        failure_reason: str | None = None,
    ) -> MealRecord:
        record.status = status
        record.completed_at = completed_at
        record.failure_reason = failure_reason
        self.db.flush()
        return record

    def delete(self, record: MealRecord) -> None:
        self.db.delete(record)
        self.db.flush()
