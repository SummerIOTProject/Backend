from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.meal import Meal
from app.models.meal_item_record import MealItemRecord
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord


class MealItemRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_or_update(self, existing: MealItemRecord | None, **kwargs) -> MealItemRecord:
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        item = MealItemRecord(**kwargs)
        self.db.add(item)
        self.db.flush()
        return item

    def get_by_record_and_meal_menu_item(self, meal_record_id: int, meal_menu_item_id: int) -> MealItemRecord | None:
        stmt = select(MealItemRecord).where(
            MealItemRecord.meal_record_id == meal_record_id,
            MealItemRecord.meal_menu_item_id == meal_menu_item_id,
        )
        return self.db.scalar(stmt)

    def list_by_record(self, meal_record_id: int) -> list[MealItemRecord]:
        stmt = (
            select(MealItemRecord)
            .options(joinedload(MealItemRecord.meal_menu_item).joinedload(MealMenuItem.menu))
            .where(MealItemRecord.meal_record_id == meal_record_id)
            .order_by(MealItemRecord.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, meal_item_record_id: int) -> MealItemRecord | None:
        stmt = (
            select(MealItemRecord)
            .options(
                joinedload(MealItemRecord.meal_record).joinedload(MealRecord.meal),
                joinedload(MealItemRecord.meal_menu_item).joinedload(MealMenuItem.menu),
            )
            .where(MealItemRecord.id == meal_item_record_id)
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def list_recent_same_menu_records(self, *, user_id: int, menu_id: int, start_date: date, end_date: date) -> list[MealItemRecord]:
        stmt = (
            select(MealItemRecord)
            .join(MealRecord, MealRecord.id == MealItemRecord.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .join(MealMenuItem, MealMenuItem.id == MealItemRecord.meal_menu_item_id)
            .options(joinedload(MealItemRecord.meal_menu_item).joinedload(MealMenuItem.menu))
            .where(
                MealRecord.user_id == user_id,
                Meal.meal_date >= start_date,
                Meal.meal_date <= end_date,
                MealMenuItem.menu_id == menu_id,
                MealRecord.status == "COMPLETED",
            )
            .order_by(Meal.meal_date.desc(), MealItemRecord.id.desc())
        )
        return list(self.db.scalars(stmt).all())

    def delete_by_record(self, meal_record_id: int) -> None:
        self.db.execute(delete(MealItemRecord).where(MealItemRecord.meal_record_id == meal_record_id))
