from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.meal import Meal
from app.models.meal_menu_item import MealMenuItem
from app.models.menu import Menu
from app.models.menu_allergen import MenuAllergen
from app.models.menu_ingredient import MenuIngredient
from app.utils.datetime import today_local
from app.utils.enums import MealType


class MealRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _query(self):
        return select(Meal).options(
            joinedload(Meal.meal_menu_items)
            .joinedload(MealMenuItem.menu)
            .joinedload(Menu.ingredients)
            .joinedload(MenuIngredient.ingredient),
            joinedload(Meal.meal_menu_items)
            .joinedload(MealMenuItem.menu)
            .joinedload(Menu.allergens)
            .joinedload(MenuAllergen.allergen),
        )

    def create(self, *, meal_date: date, meal_type: MealType, school_name: str) -> Meal:
        meal = Meal(meal_date=meal_date, meal_type=meal_type, school_name=school_name)
        self.db.add(meal)
        self.db.flush()
        return meal

    def get_by_id(self, meal_id: int) -> Meal | None:
        stmt = self._query().where(Meal.id == meal_id)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_today(self, target_date: date | None = None) -> list[Meal]:
        stmt = self._query().where(Meal.meal_date == (target_date or today_local())).order_by(Meal.meal_type.asc())
        return list(self.db.scalars(stmt).unique().all())

    def get_today_meal_by_type(self, meal_type: MealType, target_date: date | None = None) -> Meal | None:
        stmt = self._query().where(Meal.meal_date == (target_date or today_local()), Meal.meal_type == meal_type)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_unique_fields(self, *, meal_date: date, meal_type: MealType, school_name: str) -> Meal | None:
        stmt = select(Meal).where(Meal.meal_date == meal_date, Meal.meal_type == meal_type, Meal.school_name == school_name)
        return self.db.scalar(stmt)
