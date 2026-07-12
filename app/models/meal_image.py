from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK
from app.utils.enums import ImageType

if TYPE_CHECKING:
    from app.models.meal_record import MealRecord


class MealImage(Base):
    __tablename__ = "meal_images"
    __table_args__ = (UniqueConstraint("meal_record_id", "image_type", name="uq_meal_image_record_type"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    meal_record_id: Mapped[int] = mapped_column(
        ForeignKey("meal_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_type: Mapped[ImageType] = mapped_column(String(20), nullable=False)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    meal_record: Mapped["MealRecord"] = relationship(back_populates="images")
