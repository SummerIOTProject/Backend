from datetime import date, datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.models.meal import Meal
from app.models.meal_image import MealImage
from app.models.meal_item_record import MealItemRecord
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord
from app.models.menu import Menu
from app.models.menu_allergen import MenuAllergen
from app.models.menu_ingredient import MenuIngredient
from app.utils.enums import MealRecordStatus


class MealRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _query(self):
        return select(MealRecord).options(
            joinedload(MealRecord.meal)
            .joinedload(Meal.meal_menu_items)
            .joinedload(MealMenuItem.menu)
            .joinedload(Menu.ingredients)
            .joinedload(MenuIngredient.ingredient),
            joinedload(MealRecord.meal)
            .joinedload(Meal.meal_menu_items)
            .joinedload(MealMenuItem.menu)
            .joinedload(Menu.allergens)
            .joinedload(MenuAllergen.allergen),
            joinedload(MealRecord.images),
            joinedload(MealRecord.item_records)
            .joinedload(MealItemRecord.meal_menu_item)
            .joinedload(MealMenuItem.menu),
        )

    def create(self, *, user_id: int, meal_id: int) -> MealRecord:
        record = MealRecord(user_id=user_id, meal_id=meal_id, status=MealRecordStatus.CREATED)
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_id(self, meal_record_id: int) -> MealRecord | None:
        stmt = self._query().where(MealRecord.id == meal_record_id)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_user_and_meal(self, *, user_id: int, meal_id: int) -> MealRecord | None:
        stmt = select(MealRecord).where(MealRecord.user_id == user_id, MealRecord.meal_id == meal_id)
        return self.db.scalar(stmt)

    def list_recent_completed_by_user(self, *, user_id: int, start_date: date, end_date: date) -> list[MealRecord]:
        stmt = (
            self._query()
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(
                MealRecord.user_id == user_id,
                MealRecord.status == MealRecordStatus.COMPLETED,
                Meal.meal_date >= start_date,
                Meal.meal_date <= end_date,
            )
            .order_by(Meal.meal_date.desc(), MealRecord.id.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_all(self) -> list[MealRecord]:
        stmt = self._query().order_by(MealRecord.id.desc())
        return list(self.db.scalars(stmt).unique().all())

    def update_status(
        self,
        record: MealRecord,
        *,
        status: MealRecordStatus,
        completed_at: datetime | None = None,
        failure_reason: str | None = None,
    ) -> MealRecord:
        record.status = status
        record.completed_at = completed_at
        record.failure_reason = failure_reason
        self.db.flush()
        return record
