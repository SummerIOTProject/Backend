from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.menu_ingredient import MenuIngredient


class Ingredient(TimestampedModel, Base):
    __tablename__ = "ingredients"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    menus: Mapped[list["MenuIngredient"]] = relationship(back_populates="ingredient", cascade="all, delete-orphan")
