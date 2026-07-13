from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.meal_menu_item import MealMenuItem
from app.models.serving_recommendation import ServingRecommendation


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_for_meal(self, *, user_id: int, meal_id: int, items: list[ServingRecommendation]) -> list[ServingRecommendation]:
        self.db.execute(delete(ServingRecommendation).where(ServingRecommendation.user_id == user_id, ServingRecommendation.meal_id == meal_id))
        for item in items:
            self.db.add(item)
        self.db.flush()
        return items

    def list_by_user_and_meal(self, *, user_id: int, meal_id: int) -> list[ServingRecommendation]:
        stmt = (
            select(ServingRecommendation)
            .options(joinedload(ServingRecommendation.meal_menu_item).joinedload(MealMenuItem.menu))
            .where(ServingRecommendation.user_id == user_id, ServingRecommendation.meal_id == meal_id)
            .order_by(ServingRecommendation.id.asc())
        )
        return list(self.db.scalars(stmt).all())
