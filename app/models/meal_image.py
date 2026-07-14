from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import ImageType

if TYPE_CHECKING:
    from app.models.meal_record import MealRecord


class MealImage(TimestampedModel, Base):
    __tablename__ = "meal_images"
    __table_args__ = (UniqueConstraint("meal_record_id", "image_type", name="uq_meal_image_record_type"),)

    meal_record_id: Mapped[int] = mapped_column(ForeignKey("meal_records.id", ondelete="CASCADE"), nullable=False, index=True)
    image_type: Mapped[ImageType] = mapped_column(String(20), nullable=False)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    meal_record: Mapped["MealRecord"] = relationship(back_populates="images")
