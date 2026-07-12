from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.models.meal_menu_item import MealMenuItem
from app.repositories.meal_repository import MealRepository
from app.schemas.meal import MealCreateRequest, MealUpdateRequest


class MealService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_repository = MealRepository(db)

    def create_meal(self, request: MealCreateRequest):
        existing = self.meal_repository.get_by_unique_fields(
            meal_date=request.meal_date,
            meal_type=request.meal_type,
            school_name=request.school_name,
        )
        if existing:
            raise ConflictException(
                message="동일한 식단이 이미 존재합니다.",
                code="DUPLICATE_MEAL",
                detail="meal_date, meal_type, school_name 조합이 중복됩니다.",
            )
        meal = self.meal_repository.create(
            meal_date=request.meal_date,
            meal_type=request.meal_type,
            school_name=request.school_name,
        )
        for item in request.menu_items:
            self.db.add(
                MealMenuItem(
                    meal_id=meal.id,
                    name=item.name,
                    category=item.category,
                    tray_section=item.tray_section,
                    display_order=item.display_order,
                )
            )
        self.db.commit()
        return self.get_meal(meal.id)

    def get_meal(self, meal_id: int):
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(
                message="식단을 찾을 수 없습니다.",
                code="MEAL_NOT_FOUND",
                detail=f"meal_id={meal_id}",
            )
        return meal

    def list_meals(self):
        return self.meal_repository.list()

    def get_today_meals(self):
        return self.meal_repository.get_today()

    def update_meal(self, meal_id: int, request: MealUpdateRequest):
        meal = self.get_meal(meal_id)
        target_date = request.meal_date or meal.meal_date
        target_type = request.meal_type or meal.meal_type
        target_school = request.school_name or meal.school_name
        duplicate = self.meal_repository.get_by_unique_fields(
            meal_date=target_date,
            meal_type=target_type,
            school_name=target_school,
        )
        if duplicate and duplicate.id != meal.id:
            raise ConflictException(
                message="동일한 식단이 이미 존재합니다.",
                code="DUPLICATE_MEAL",
                detail="meal_date, meal_type, school_name 조합이 중복됩니다.",
            )
        payload = request.model_dump(exclude_unset=True, exclude={"menu_items"})
        self.meal_repository.update(meal, **payload)
        if request.menu_items is not None:
            meal.menu_items.clear()
            self.db.flush()
            for item in request.menu_items:
                meal.menu_items.append(
                    MealMenuItem(
                        name=item.name,
                        category=item.category,
                        tray_section=item.tray_section,
                        display_order=item.display_order,
                    )
                )
        self.db.commit()
        return self.get_meal(meal.id)

    def delete_meal(self, meal_id: int) -> None:
        meal = self.get_meal(meal_id)
        self.meal_repository.delete(meal)
        self.db.commit()
