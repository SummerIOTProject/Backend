from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient
    from app.models.menu import Menu


class MenuIngredient(Base):
    __tablename__ = "menu_ingredients"
    __table_args__ = (UniqueConstraint("menu_id", "ingredient_id", name="uq_menu_ingredient"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)

    menu: Mapped["Menu"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="menus")
