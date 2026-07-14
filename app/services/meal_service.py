from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.meal_menu_item import MealMenuItem
from app.repositories.meal_repository import MealRepository
from app.repositories.menu_repository import MenuRepository
from app.schemas.meal import MealCreateRequest


class MealService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_repository = MealRepository(db)
        self.menu_repository = MenuRepository(db)

    def create_meal(self, request: MealCreateRequest):
        if self.meal_repository.get_by_unique_fields(
            meal_date=request.meal_date,
            meal_type=request.meal_type,
            school_name=request.school_name,
        ):
            raise ConflictException(message="동일한 급식이 이미 존재합니다.", code="DUPLICATE_MEAL", detail="duplicate meal")
        if len(set(request.menu_ids)) != len(request.menu_ids):
            raise BadRequestException(message="중복된 메뉴 ID가 포함되어 있습니다.", code="DUPLICATE_MENU_ID", detail="menu_ids contains duplicates")
        try:
            meal = self.meal_repository.create(
                meal_date=request.meal_date,
                meal_type=request.meal_type,
                school_name=request.school_name,
            )
            for menu_id in request.menu_ids:
                menu = self.menu_repository.get_by_id(menu_id)
                if not menu:
                    raise NotFoundException(message="메뉴를 찾을 수 없습니다.", code="MENU_NOT_FOUND", detail=f"menu_id={menu_id}")
                if not menu.is_active:
                    raise BadRequestException(message="비활성 메뉴는 급식에 등록할 수 없습니다.", code="MENU_INACTIVE", detail=f"menu_id={menu_id}")
                self.db.add(MealMenuItem(meal_id=meal.id, menu_id=menu_id))
            self.db.commit()
            return self.get_meal(meal.id)
        except Exception:
            self.db.rollback()
            raise

    def get_meal(self, meal_id: int):
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_id={meal_id}")
        return meal

    def get_today_meals(self):
        return self.meal_repository.get_today(school_name=settings.SCHOOL_NAME)

    def get_today_meal_by_type(self, meal_type):
        meal = self.meal_repository.get_today_meal_by_type(meal_type, school_name=settings.SCHOOL_NAME)
        if not meal:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_type={meal_type}")
        return meal
