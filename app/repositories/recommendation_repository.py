from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.meal_analysis import MealAnalysis
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord
from app.models.serving_recommendation import ServingRecommendation
from app.utils.enums import MealRecordStatus


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        meal_menu_item_id: int,
        recommendation_level,
        average_consumed_ratio: float | None,
        reason: str,
    ) -> ServingRecommendation:
        recommendation = ServingRecommendation(
            user_id=user_id,
            meal_menu_item_id=meal_menu_item_id,
            recommendation_level=recommendation_level,
            average_consumed_ratio=average_consumed_ratio,
            reason=reason,
        )
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def list_by_user(self, user_id: int) -> list[ServingRecommendation]:
        stmt = (
            select(ServingRecommendation)
            .options(joinedload(ServingRecommendation.meal_menu_item))
            .where(ServingRecommendation.user_id == user_id)
            .order_by(ServingRecommendation.created_at.desc(), ServingRecommendation.id.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_by_user_and_meal_menu_items(self, *, user_id: int, meal_menu_item_ids: list[int]) -> list[ServingRecommendation]:
        if not meal_menu_item_ids:
            return []
        stmt = (
            select(ServingRecommendation)
            .options(joinedload(ServingRecommendation.meal_menu_item))
            .where(
                ServingRecommendation.user_id == user_id,
                ServingRecommendation.meal_menu_item_id.in_(meal_menu_item_ids),
            )
            .order_by(ServingRecommendation.meal_menu_item_id.asc(), ServingRecommendation.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_recent_same_menu_ratios(self, *, user_id: int, menu_name: str, limit: int = 3) -> list[float]:
        stmt = (
            select(MealAnalysis.consumed_ratio)
            .join(MealAnalysis.meal_menu_item)
            .join(MealAnalysis.meal_record)
            .where(
                MealRecord.user_id == user_id,
                MealRecord.status == MealRecordStatus.COMPLETED,
                MealMenuItem.name == menu_name,
            )
            .order_by(MealRecord.completed_at.desc().nullslast(), MealRecord.id.desc())
            .limit(limit)
        )
        return [float(value) for value in self.db.scalars(stmt).all()]

    def delete_by_user_and_meal_menu_items(self, user_id: int, meal_menu_item_ids: list[int]) -> None:
        if not meal_menu_item_ids:
            return
        stmt = select(ServingRecommendation).where(
            ServingRecommendation.user_id == user_id,
            ServingRecommendation.meal_menu_item_id.in_(meal_menu_item_ids),
        )
        for item in self.db.scalars(stmt).all():
            self.db.delete(item)
        self.db.flush()
