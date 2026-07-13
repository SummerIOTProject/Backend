from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK

if TYPE_CHECKING:
    from app.models.allergen import Allergen
    from app.models.menu import Menu


class MenuAllergen(Base):
    __tablename__ = "menu_allergens"
    __table_args__ = (UniqueConstraint("menu_id", "allergen_id", name="uq_menu_allergen"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_id: Mapped[int] = mapped_column(ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False, index=True)

    menu: Mapped["Menu"] = relationship(back_populates="allergens")
    allergen: Mapped["Allergen"] = relationship(back_populates="menus")
