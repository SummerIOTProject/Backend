from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK
from app.utils.enums import MealRecordStatus

if TYPE_CHECKING:
    from app.models.meal import Meal
    from app.models.meal_analysis import MealAnalysis
    from app.models.meal_image import MealImage
    from app.models.user import User


class MealRecord(Base):
    __tablename__ = "meal_records"
    __table_args__ = (UniqueConstraint("user_id", "meal_id", name="uq_meal_record_user_meal"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[MealRecordStatus] = mapped_column(String(30), nullable=False, default=MealRecordStatus.CREATED)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="meal_records")
    meal: Mapped["Meal"] = relationship(back_populates="meal_records")
    images: Mapped[list["MealImage"]] = relationship(back_populates="meal_record", cascade="all, delete-orphan")
    analyses: Mapped[list["MealAnalysis"]] = relationship(
        back_populates="meal_record",
        cascade="all, delete-orphan",
    )
