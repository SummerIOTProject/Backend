from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import RecommendationLevel


class ServingRecommendation(TimestampedModel, Base):
    __tablename__ = "serving_recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "meal_id", "meal_menu_item_id", name="uq_serving_recommendation_user_meal_item"),
        CheckConstraint("recommended_serving_ratio > 0", name="ck_serving_recommendations_ratio_positive"),
        CheckConstraint("recommended_serving_g >= 0", name="ck_serving_recommendations_serving_g_nonnegative"),
        CheckConstraint(
            "recent_average_consumed_ratio IS NULL OR (recent_average_consumed_ratio >= 0 AND recent_average_consumed_ratio <= 1)",
            name="ck_serving_recommendations_recent_avg_range",
        ),
        CheckConstraint("sample_count >= 0", name="ck_serving_recommendations_sample_count_nonnegative"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("meal_menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_level: Mapped[RecommendationLevel] = mapped_column(String(20), nullable=False)
    recommended_serving_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_serving_g: Mapped[float] = mapped_column(Float, nullable=False)
    recent_average_consumed_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    user = relationship("User", back_populates="recommendations")
    meal_menu_item = relationship("MealMenuItem", back_populates="recommendations")
