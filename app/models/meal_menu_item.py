from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK

if TYPE_CHECKING:
    from app.models.meal import Meal
    from app.models.meal_item_record import MealItemRecord
    from app.models.menu import Menu
    from app.models.serving_recommendation import ServingRecommendation


class MealMenuItem(Base):
    __tablename__ = "meal_menu_items"
    __table_args__ = (UniqueConstraint("meal_id", "menu_id", name="uq_meal_menu_item"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="RESTRICT"), nullable=False, index=True)

    meal: Mapped["Meal"] = relationship(back_populates="meal_menu_items")
    menu: Mapped["Menu"] = relationship(back_populates="meal_menu_items")
    item_records: Mapped[list["MealItemRecord"]] = relationship(back_populates="meal_menu_item", cascade="all, delete-orphan")
    recommendations: Mapped[list["ServingRecommendation"]] = relationship(back_populates="meal_menu_item", cascade="all, delete-orphan")
