from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import ConsumptionLevel

if TYPE_CHECKING:
    from app.models.meal_menu_item import MealMenuItem
    from app.models.meal_record import MealRecord


class MealAnalysis(TimestampedModel, Base):
    __tablename__ = "meal_analyses"
    __table_args__ = (UniqueConstraint("meal_record_id", "meal_menu_item_id", name="uq_analysis_record_menu"),)

    meal_record_id: Mapped[int] = mapped_column(
        ForeignKey("meal_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("meal_menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consumed_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    consumption_level: Mapped[ConsumptionLevel] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    meal_record: Mapped["MealRecord"] = relationship(back_populates="analyses")
    meal_menu_item: Mapped["MealMenuItem"] = relationship(back_populates="analyses")

    @property
    def menu_name(self) -> str:
        return self.meal_menu_item.name if self.meal_menu_item else ""
