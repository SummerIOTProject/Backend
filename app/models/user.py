from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel
from app.utils.enums import UserRole

if TYPE_CHECKING:
    from app.models.meal_image import MealImage
    from app.models.meal_item_record import MealItemRecord
    from app.models.meal_record import MealRecord
    from app.models.refresh_token import RefreshToken
    from app.models.rfid_card import RFIDCard
    from app.models.serving_recommendation import ServingRecommendation
    from app.models.user_allergy import UserAllergy


class User(TimestampedModel, Base):
    __tablename__ = "users"

    login_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    student_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rfid_cards: Mapped[list["RFIDCard"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    allergies: Mapped[list["UserAllergy"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    meal_records: Mapped[list["MealRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    corrected_meal_item_records: Mapped[list["MealItemRecord"]] = relationship(back_populates="corrected_by_user")
    recommendations: Mapped[list["ServingRecommendation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
