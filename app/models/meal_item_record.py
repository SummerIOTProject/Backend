from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import AnalysisType, ConsumptionLevel

if TYPE_CHECKING:
    from app.models.meal_menu_item import MealMenuItem
    from app.models.meal_record import MealRecord
    from app.models.user import User


class MealItemRecord(TimestampedModel, Base):
    __tablename__ = "meal_item_records"
    __table_args__ = (
        UniqueConstraint("meal_record_id", "meal_menu_item_id", name="uq_meal_item_record"),
        CheckConstraint("consumed_ratio >= 0 AND consumed_ratio <= 1", name="ck_meal_item_records_consumed_ratio_range"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_meal_item_records_confidence_range"),
    )

    meal_record_id: Mapped[int] = mapped_column(ForeignKey("meal_records.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_menu_item_id: Mapped[int] = mapped_column(ForeignKey("meal_menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    consumed_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    consumption_level: Mapped[ConsumptionLevel] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    corrected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_type: Mapped[AnalysisType] = mapped_column(String(30), nullable=False, default=AnalysisType.MOCK)

    meal_record: Mapped["MealRecord"] = relationship(back_populates="item_records")
    meal_menu_item: Mapped["MealMenuItem"] = relationship(back_populates="item_records")
    corrected_by_user: Mapped["User | None"] = relationship(back_populates="corrected_meal_item_records")
