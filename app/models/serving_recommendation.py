from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK
from app.utils.enums import RecommendationLevel

if TYPE_CHECKING:
    from app.models.meal_menu_item import MealMenuItem
    from app.models.user import User


class ServingRecommendation(Base):
    __tablename__ = "serving_recommendations"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("meal_menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_level: Mapped[RecommendationLevel] = mapped_column(String(20), nullable=False)
    average_consumed_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="serving_recommendations")
    meal_menu_item: Mapped["MealMenuItem"] = relationship(back_populates="recommendations")
