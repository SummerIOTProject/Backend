from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.meal import Meal
from app.models.meal_menu_item import MealMenuItem
from app.utils.enums import MealType


class MealRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, meal_date: date, meal_type: MealType, school_name: str) -> Meal:
        meal = Meal(meal_date=meal_date, meal_type=meal_type, school_name=school_name)
        self.db.add(meal)
        self.db.flush()
        return meal

    def get_by_id(self, meal_id: int) -> Meal | None:
        stmt = select(Meal).options(joinedload(Meal.menu_items)).where(Meal.id == meal_id)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_today(self, *, meal_date: date | None = None) -> list[Meal]:
        target_date = meal_date or date.today()
        stmt = select(Meal).options(joinedload(Meal.menu_items)).where(Meal.meal_date == target_date).order_by(Meal.id.asc())
        return list(self.db.scalars(stmt).unique().all())

    def list(self) -> list[Meal]:
        stmt = select(Meal).options(joinedload(Meal.menu_items)).order_by(Meal.meal_date.desc(), Meal.id.asc())
        return list(self.db.scalars(stmt).unique().all())

    def update(self, meal: Meal, **kwargs: object) -> Meal:
        for key, value in kwargs.items():
            setattr(meal, key, value)
        self.db.flush()
        return meal

    def delete(self, meal: Meal) -> None:
        self.db.delete(meal)
        self.db.flush()

    def get_menu_items(self, meal_id: int) -> list[MealMenuItem]:
        stmt = select(MealMenuItem).where(MealMenuItem.meal_id == meal_id).order_by(MealMenuItem.display_order.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_unique_fields(self, *, meal_date: date, meal_type: MealType, school_name: str) -> Meal | None:
        stmt = select(Meal).where(
            Meal.meal_date == meal_date,
            Meal.meal_type == meal_type,
            Meal.school_name == school_name,
        )
        return self.db.scalar(stmt)
