from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.meal_record import MealRecord
    from app.models.rfid_card import RFIDCard
    from app.models.serving_recommendation import ServingRecommendation


class User(TimestampedModel, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    student_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="STUDENT", server_default="STUDENT")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    rfid_cards: Mapped[list["RFIDCard"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    meal_records: Mapped[list["MealRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    serving_recommendations: Mapped[list["ServingRecommendation"]] = relationship(back_populates="user")
