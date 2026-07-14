from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.ingredient import Ingredient
from app.models.menu import Menu
from app.models.menu_allergen import MenuAllergen
from app.models.menu_ingredient import MenuIngredient


class MenuRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _query(self):
        return select(Menu).options(
            joinedload(Menu.ingredients).joinedload(MenuIngredient.ingredient),
            joinedload(Menu.allergens).joinedload(MenuAllergen.allergen),
        )

    def create(self, **kwargs) -> Menu:
        menu = Menu(**kwargs)
        self.db.add(menu)
        self.db.flush()
        return menu

    def get_by_id(self, menu_id: int) -> Menu | None:
        stmt = self._query().where(Menu.id == menu_id)
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_name(self, name: str) -> Menu | None:
        stmt = self._query().where(Menu.name == name)
        return self.db.scalars(stmt).unique().one_or_none()

    def list(self, *, include_inactive: bool = False) -> list[Menu]:
        stmt = self._query()
        if not include_inactive:
            stmt = stmt.where(Menu.is_active.is_(True))
        stmt = stmt.order_by(Menu.name.asc())
        return list(self.db.scalars(stmt).unique().all())

    def update(self, menu: Menu, **kwargs) -> Menu:
        for key, value in kwargs.items():
            setattr(menu, key, value)
        self.db.flush()
        return menu

    def deactivate(self, menu: Menu) -> None:
        menu.is_active = False
        self.db.flush()

    def get_or_create_ingredient(self, name: str) -> Ingredient:
        stmt = select(Ingredient).where(Ingredient.name == name)
        ingredient = self.db.scalar(stmt)
        if ingredient:
            return ingredient
        ingredient = Ingredient(name=name)
        self.db.add(ingredient)
        self.db.flush()
        return ingredient
