from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.meal_menu_item import MealMenuItem
    from app.models.menu_allergen import MenuAllergen
    from app.models.menu_ingredient import MenuIngredient


class Menu(TimestampedModel, Base):
    __tablename__ = "menus"
    __table_args__ = (
        CheckConstraint("standard_serving_g > 0", name="ck_menus_standard_serving_g_positive"),
        CheckConstraint("calories_per_100g >= 0", name="ck_menus_calories_nonnegative"),
        CheckConstraint("carbohydrate_per_100g >= 0", name="ck_menus_carbohydrate_nonnegative"),
        CheckConstraint("protein_per_100g >= 0", name="ck_menus_protein_nonnegative"),
        CheckConstraint("fat_per_100g >= 0", name="ck_menus_fat_nonnegative"),
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    standard_serving_g: Mapped[float] = mapped_column(Float, nullable=False)
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbohydrate_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ingredients: Mapped[list["MenuIngredient"]] = relationship(back_populates="menu", cascade="all, delete-orphan")
    allergens: Mapped[list["MenuAllergen"]] = relationship(back_populates="menu", cascade="all, delete-orphan")
    meal_menu_items: Mapped[list["MealMenuItem"]] = relationship(back_populates="menu")
