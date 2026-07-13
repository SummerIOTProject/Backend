from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.menu_allergen import MenuAllergen
    from app.models.user_allergy import UserAllergy


class Allergen(TimestampedModel, Base):
    __tablename__ = "allergens"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name_ko: Mapped[str] = mapped_column(String(100), nullable=False)
    display_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list["UserAllergy"]] = relationship(back_populates="allergen", cascade="all, delete-orphan")
    menus: Mapped[list["MenuAllergen"]] = relationship(back_populates="allergen", cascade="all, delete-orphan")
