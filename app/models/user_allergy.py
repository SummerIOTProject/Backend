from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_PK

if TYPE_CHECKING:
    from app.models.allergen import Allergen
    from app.models.user import User


class UserAllergy(Base):
    __tablename__ = "user_allergies"
    __table_args__ = (UniqueConstraint("user_id", "allergen_id", name="uq_user_allergy"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_id: Mapped[int] = mapped_column(ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="allergies")
    allergen: Mapped["Allergen"] = relationship(back_populates="users")
