from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.meal import Meal
from app.models.meal_item_record import MealItemRecord
from app.models.meal_menu_item import MealMenuItem
from app.models.meal_record import MealRecord
from app.models.serving_recommendation import ServingRecommendation
from app.models.user import User
from app.repositories.meal_item_record_repository import MealItemRecordRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.utils.datetime import get_current_date, get_recent_start_date
from app.utils.enums import RecommendationLevel, UserRole


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meal_repository = MealRepository(db)
        self.meal_item_record_repository = MealItemRecordRepository(db)
        self.meal_record_repository = MealRecordRepository(db)
        self.recommendation_repository = RecommendationRepository(db)

    def generate_for_meal(self, *, user_id: int, meal_id: int):
        meal = self.meal_repository.get_by_id(meal_id)
        if not meal:
            raise NotFoundException(message="급식을 찾을 수 없습니다.", code="MEAL_NOT_FOUND", detail=f"meal_id={meal_id}")
        start_date = get_recent_start_date(5)
        end_date = get_current_date()
        items = []
        for meal_menu_item in meal.meal_menu_items:
            recent = self.meal_item_record_repository.list_recent_same_menu_records(
                user_id=user_id,
                menu_id=meal_menu_item.menu_id,
                start_date=start_date,
                end_date=end_date,
                exclude_meal_id=meal_id,
            )
            ratios = [item.consumed_ratio for item in recent]
            if not ratios:
                level = RecommendationLevel.NORMAL
                ratio = 1.0
                avg_ratio = None
                reason = "이전 섭취 기록이 없어 기준 제공량을 추천합니다."
            else:
                avg_ratio = round(mean(ratios), 2)
                if avg_ratio < 0.50:
                    level = RecommendationLevel.LESS
                    ratio = 0.6
                elif avg_ratio < 0.70:
                    level = RecommendationLevel.LESS
                    ratio = 0.8
                else:
                    level = RecommendationLevel.NORMAL
                    ratio = 1.0
                if len(ratios) == 1:
                    reason = "최근 데이터가 1건뿐이므로 참고용 추천입니다."
                else:
                    reason = f"최근 5일 동일 메뉴 평균 섭취율이 {round(avg_ratio * 100, 2)}%입니다."
            items.append(
                ServingRecommendation(
                    user_id=user_id,
                    meal_id=meal_id,
                    meal_menu_item_id=meal_menu_item.id,
                    recommendation_level=level,
                    recommended_serving_ratio=ratio,
                    recommended_serving_g=round(meal_menu_item.menu.standard_serving_g * ratio, 2),
                    recent_average_consumed_ratio=avg_ratio,
                    sample_count=len(ratios),
                    reason=reason,
                )
            )
        self.recommendation_repository.replace_for_meal(user_id=user_id, meal_id=meal_id, items=items)
        self.db.commit()
        return self.recommendation_repository.list_by_user_and_meal(user_id=user_id, meal_id=meal_id)

    def get_dashboard(self, target_date):
        active_user_count = self.db.scalar(
            select(func.count(User.id)).where(User.is_active.is_(True), User.role == UserRole.STUDENT)
        ) or 0
        meal_record_count = self.db.scalar(
            select(func.count(MealRecord.id)).join(Meal, Meal.id == MealRecord.meal_id).where(Meal.meal_date == target_date)
        ) or 0
        completed_analysis_count = self.db.scalar(
            select(func.count(MealRecord.id)).join(Meal, Meal.id == MealRecord.meal_id).where(Meal.meal_date == target_date, MealRecord.status == "COMPLETED")
        ) or 0
        failed_analysis_count = self.db.scalar(
            select(func.count(MealRecord.id)).join(Meal, Meal.id == MealRecord.meal_id).where(Meal.meal_date == target_date, MealRecord.status == "FAILED")
        ) or 0
        analysis_sample_count = self.db.scalar(
            select(func.count(MealItemRecord.id))
            .join(MealRecord, MealRecord.id == MealItemRecord.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date == target_date, MealRecord.status == "COMPLETED")
        ) or 0
        avg_ratio = self.db.scalar(
            select(func.avg(MealItemRecord.consumed_ratio))
            .join(MealRecord, MealRecord.id == MealItemRecord.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date == target_date, MealRecord.status == "COMPLETED")
        )
        avg_ratio_value = round(float(avg_ratio), 2) if avg_ratio is not None else None
        return {
            "date": target_date,
            "active_user_count": int(active_user_count),
            "meal_record_count": int(meal_record_count),
            "completed_analysis_count": int(completed_analysis_count),
            "failed_analysis_count": int(failed_analysis_count),
            "analysis_sample_count": int(analysis_sample_count),
            "average_consumed_ratio": avg_ratio_value,
            "average_leftover_ratio": round(1 - avg_ratio_value, 2) if avg_ratio_value is not None else None,
        }

    def get_leftover_summary(self, start_date, end_date):
        stmt = (
            select(
                MealMenuItem.menu_id,
                func.min(MealMenuItem.menu_id),
                func.avg(MealItemRecord.consumed_ratio),
                func.count(MealItemRecord.id),
            )
            .join(MealMenuItem, MealMenuItem.id == MealItemRecord.meal_menu_item_id)
            .join(MealRecord, MealRecord.id == MealItemRecord.meal_record_id)
            .join(Meal, Meal.id == MealRecord.meal_id)
            .where(Meal.meal_date >= start_date, Meal.meal_date <= end_date)
            .group_by(MealMenuItem.menu_id)
        )
        result = []
        for menu_id, _, avg_ratio, count in self.db.execute(stmt):
            ratio = round(float(avg_ratio), 2) if avg_ratio is not None else None
            meal_menu_item = self.db.scalar(select(MealMenuItem).where(MealMenuItem.menu_id == menu_id))
            result.append(
                {
                    "menu_id": menu_id,
                    "menu_name": meal_menu_item.menu.name if meal_menu_item else str(menu_id),
                    "analysis_count": int(count),
                    "average_consumed_ratio": ratio,
                    "average_leftover_ratio": round(1 - ratio, 2) if ratio is not None else None,
                }
            )
        return result
