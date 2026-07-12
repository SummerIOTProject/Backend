from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK

if TYPE_CHECKING:
    from app.models.meal import Meal
    from app.models.meal_analysis import MealAnalysis
    from app.models.serving_recommendation import ServingRecommendation


class MealMenuItem(Base):
    __tablename__ = "meal_menu_items"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tray_section: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    meal: Mapped["Meal"] = relationship(back_populates="menu_items")
    analyses: Mapped[list["MealAnalysis"]] = relationship(back_populates="meal_menu_item")
    recommendations: Mapped[list["ServingRecommendation"]] = relationship(back_populates="meal_menu_item")
