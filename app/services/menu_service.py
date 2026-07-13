from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.menu_allergen import MenuAllergen
from app.models.menu_ingredient import MenuIngredient
from app.repositories.allergen_repository import AllergenRepository
from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import MenuCreateRequest, MenuUpdateRequest
from app.utils.normalization import normalize_allergen_codes, normalize_ingredient_names


class MenuService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.menu_repository = MenuRepository(db)
        self.allergen_repository = AllergenRepository(db)

    def create_menu(self, request: MenuCreateRequest):
        if self.menu_repository.get_by_name(request.name):
            raise ConflictException(message="이미 등록된 메뉴입니다.", code="DUPLICATE_MENU_NAME", detail=request.name)
        normalized_ingredients = normalize_ingredient_names(request.ingredients)
        normalized_allergen_codes = normalize_allergen_codes(request.allergen_codes)
        try:
            menu = self.menu_repository.create(
                name=request.name,
                standard_serving_g=request.standard_serving_g,
                calories_per_100g=request.nutrition_per_100g.calories_kcal,
                carbohydrate_per_100g=request.nutrition_per_100g.carbohydrate_g,
                protein_per_100g=request.nutrition_per_100g.protein_g,
                fat_per_100g=request.nutrition_per_100g.fat_g,
                is_active=True,
            )
            self._replace_links(menu, normalized_ingredients, normalized_allergen_codes)
            self.db.commit()
            return self.get_menu(menu.id)
        except Exception:
            self.db.rollback()
            raise

    def _replace_links(self, menu, ingredients: list[str] | None, allergen_codes: list[str] | None) -> None:
        if ingredients is not None:
            menu.ingredients.clear()
            self.db.flush()
            for name in ingredients:
                ingredient = self.menu_repository.get_or_create_ingredient(name)
                menu.ingredients.append(MenuIngredient(menu_id=menu.id, ingredient_id=ingredient.id))
        if allergen_codes is not None:
            menu.allergens.clear()
            self.db.flush()
            allergens = self.allergen_repository.get_by_codes(allergen_codes)
            if len(allergens) != len(set(allergen_codes)):
                raise BadRequestException(message="유효하지 않은 알레르기 코드가 있습니다.", code="INVALID_ALLERGEN_CODE", detail="unknown allergen code")
            for allergen in allergens:
                menu.allergens.append(MenuAllergen(menu_id=menu.id, allergen_id=allergen.id))

    def get_menu(self, menu_id: int):
        menu = self.menu_repository.get_by_id(menu_id)
        if not menu:
            raise NotFoundException(message="메뉴를 찾을 수 없습니다.", code="MENU_NOT_FOUND", detail=f"menu_id={menu_id}")
        return menu

    def list_menus(self, *, include_inactive: bool = False):
        return self.menu_repository.list(include_inactive=include_inactive)

    def update_menu(self, menu_id: int, request: MenuUpdateRequest):
        menu = self.get_menu(menu_id)
        payload = {}
        if request.name is not None:
            duplicate = self.menu_repository.get_by_name(request.name)
            if duplicate and duplicate.id != menu_id:
                raise ConflictException(message="이미 등록된 메뉴입니다.", code="DUPLICATE_MENU_NAME", detail=request.name)
            payload["name"] = request.name
        if request.standard_serving_g is not None:
            payload["standard_serving_g"] = request.standard_serving_g
        if request.is_active is not None:
            payload["is_active"] = request.is_active
        if request.nutrition_per_100g is not None:
            payload.update(
                calories_per_100g=request.nutrition_per_100g.calories_kcal,
                carbohydrate_per_100g=request.nutrition_per_100g.carbohydrate_g,
                protein_per_100g=request.nutrition_per_100g.protein_g,
                fat_per_100g=request.nutrition_per_100g.fat_g,
            )
        try:
            self.menu_repository.update(menu, **payload)
            normalized_ingredients = normalize_ingredient_names(request.ingredients) if request.ingredients is not None else None
            normalized_allergen_codes = normalize_allergen_codes(request.allergen_codes) if request.allergen_codes is not None else None
            self._replace_links(menu, normalized_ingredients, normalized_allergen_codes)
            self.db.commit()
            return self.get_menu(menu.id)
        except Exception:
            self.db.rollback()
            raise

    def delete_menu(self, menu_id: int) -> None:
        menu = self.get_menu(menu_id)
        self.menu_repository.deactivate(menu)
        self.db.commit()
