from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.meal_analysis import MealAnalysis
from app.models.meal import Meal
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord
from app.models.user import User
from app.repositories.meal_repository import MealRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.utils.enums import RecommendationLevel


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.meal_repository = MealRepository(db)
        self.recommendation_repository = RecommendationRepository(db)

    def generate_recommendations(self, *, user_id: int, meal_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}",
            )
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(
                message="식단을 찾을 수 없습니다.",
                code="MEAL_NOT_FOUND",
                detail=f"meal_id={meal_id}",
            )
        menu_item_ids = [item.id for item in meal.menu_items]
        self.recommendation_repository.delete_by_user_and_meal_menu_items(user_id, menu_item_ids)
        created = []
        for menu_item in meal.menu_items:
            ratios = self.recommendation_repository.get_recent_same_menu_ratios(user_id=user_id, menu_name=menu_item.name)
            if not ratios:
                level = RecommendationLevel.NORMAL
                avg_ratio = None
                reason = "이전 동일 메뉴 섭취 기록이 없어 기본 배식 단계(NORMAL)를 추천합니다."
            else:
                avg_ratio = round(mean(ratios), 2)
                if avg_ratio < 0.6:
                    level = RecommendationLevel.LESS
                    reason = f"최근 동일 메뉴 평균 섭취율이 {avg_ratio:.2f}로 낮아 적은 배식(LESS)을 추천합니다."
                else:
                    level = RecommendationLevel.NORMAL
                    reason = f"최근 동일 메뉴 평균 섭취율이 {avg_ratio:.2f}로 안정적이어서 일반 배식(NORMAL)을 추천합니다."
            created.append(
                self.recommendation_repository.create(
                    user_id=user_id,
                    meal_menu_item_id=menu_item.id,
                    recommendation_level=level,
                    average_consumed_ratio=avg_ratio,
                    reason=reason,
                )
            )
        self.db.commit()
        return created

    def get_recommendations_for_meal(self, *, user_id: int, meal_id: int):
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(
                message="식단을 찾을 수 없습니다.",
                code="MEAL_NOT_FOUND",
                detail=f"meal_id={meal_id}",
            )
        menu_item_ids = [item.id for item in meal.menu_items]
        items = self.recommendation_repository.list_by_user_and_meal_menu_items(
            user_id=user_id,
            meal_menu_item_ids=menu_item_ids,
        )
        if not items:
            items = self.generate_recommendations(user_id=user_id, meal_id=meal_id)
        return items

    def list_history(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}",
            )
        return self.recommendation_repository.list_by_user(user_id)

    def get_admin_dashboard(self, date_value):
        user_count = self.db.scalar(select(func.count(User.id)).where(func.date(User.created_at) == str(date_value))) or 0
        meal_record_count = self.db.scalar(
            select(func.count(MealRecord.id)).join(Meal, Meal.id == MealRecord.meal_id).where(Meal.meal_date == date_value)
        ) or 0
        completed_analysis_count = self.db.scalar(
            select(func.count(MealAnalysis.id))
            .join(MealRecord, MealRecord.id == MealAnalysis.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date == date_value)
        ) or 0
        avg_consumed_ratio = self.db.scalar(
            select(func.avg(MealAnalysis.consumed_ratio))
            .join(MealRecord, MealRecord.id == MealAnalysis.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date == date_value)
        )
        avg_consumed_ratio = round(float(avg_consumed_ratio or 0.0), 2)
        return {
            "date": str(date_value),
            "registered_user_count": int(user_count),
            "meal_record_count": int(meal_record_count),
            "completed_analysis_count": int(completed_analysis_count),
            "average_consumed_ratio": avg_consumed_ratio,
            "average_leftover_ratio": round(1 - avg_consumed_ratio, 2),
        }

    def get_leftover_summary(self, *, start_date, end_date):
        stmt = (
            select(
                MealMenuItem.name.label("menu_name"),
                func.avg(MealAnalysis.consumed_ratio).label("average_consumed_ratio"),
                func.count(MealAnalysis.id).label("analysis_count"),
            )
            .join(MealAnalysis.meal_menu_item)
            .join(MealRecord, MealRecord.id == MealAnalysis.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date >= start_date, Meal.meal_date <= end_date)
            .group_by(MealMenuItem.name)
            .order_by(MealMenuItem.name.asc())
        )
        items = []
        for row in self.db.execute(stmt):
            avg_ratio = round(float(row.average_consumed_ratio or 0.0), 2)
            items.append(
                {
                    "menu_name": row.menu_name,
                    "average_consumed_ratio": avg_ratio,
                    "average_leftover_ratio": round(1 - avg_ratio, 2),
                    "analysis_count": int(row.analysis_count),
                }
            )
        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "items": items,
        }

    def get_consumption_summary(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}",
            )
        stmt = (
            select(
                func.count(MealAnalysis.id).label("analysis_count"),
                func.avg(MealAnalysis.consumed_ratio).label("average_consumed_ratio"),
            )
            .join(MealRecord, MealRecord.id == MealAnalysis.meal_record_id)
            .where(MealRecord.user_id == user_id)
        )
        row = self.db.execute(stmt).one()
        avg_ratio = round(float(row.average_consumed_ratio or 0.0), 2)
        return {
            "user_id": user_id,
            "analysis_count": int(row.analysis_count or 0),
            "average_consumed_ratio": avg_ratio,
            "average_leftover_ratio": round(1 - avg_ratio, 2),
        }
