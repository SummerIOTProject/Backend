from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import MealType

if TYPE_CHECKING:
    from app.models.meal_menu_item import MealMenuItem
    from app.models.meal_record import MealRecord


class Meal(TimestampedModel, Base):
    __tablename__ = "meals"
    __table_args__ = (
        UniqueConstraint("meal_date", "meal_type", "school_name", name="uq_meal_date_type_school"),
    )

    meal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[MealType] = mapped_column(String(20), nullable=False, index=True)
    school_name: Mapped[str] = mapped_column(String(100), nullable=False)

    menu_items: Mapped[list["MealMenuItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        order_by="MealMenuItem.display_order",
    )
    meal_records: Mapped[list["MealRecord"]] = relationship(back_populates="meal", cascade="all, delete-orphan")
