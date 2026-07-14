from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.database import SessionLocal
from app.models import Allergen, Ingredient, Meal, MealMenuItem, Menu, MenuAllergen, MenuIngredient
from app.utils.enums import MealType


MENU_SPECS = [
    {
        "name": "쌀밥",
        "standard_serving_g": 210,
        "nutrition": {"calories": 150, "carbohydrate": 33, "protein": 3, "fat": 0.4},
        "ingredients": ["쌀"],
        "allergens": [],
    },
    {
        "name": "잡곡밥",
        "standard_serving_g": 210,
        "nutrition": {"calories": 155, "carbohydrate": 31, "protein": 4, "fat": 1.2},
        "ingredients": ["쌀", "보리", "현미", "흑미"],
        "allergens": [],
    },
    {
        "name": "김치볶음밥",
        "standard_serving_g": 240,
        "nutrition": {"calories": 182, "carbohydrate": 28, "protein": 5, "fat": 5},
        "ingredients": ["쌀", "김치", "대파", "양파", "간장"],
        "allergens": ["SOYBEAN"],
    },
    {
        "name": "소고기미역국",
        "standard_serving_g": 220,
        "nutrition": {"calories": 62, "carbohydrate": 3, "protein": 6, "fat": 2.8},
        "ingredients": ["미역", "소고기", "마늘", "간장"],
        "allergens": ["BEEF", "SOYBEAN"],
    },
    {
        "name": "된장국",
        "standard_serving_g": 220,
        "nutrition": {"calories": 38, "carbohydrate": 4, "protein": 3, "fat": 1.3},
        "ingredients": ["된장", "두부", "애호박", "양파"],
        "allergens": ["SOYBEAN"],
    },
    {
        "name": "콩나물국",
        "standard_serving_g": 220,
        "nutrition": {"calories": 24, "carbohydrate": 2.5, "protein": 2.3, "fat": 0.7},
        "ingredients": ["콩나물", "대파", "마늘", "국간장"],
        "allergens": ["SOYBEAN"],
    },
    {
        "name": "제육볶음",
        "standard_serving_g": 140,
        "nutrition": {"calories": 210, "carbohydrate": 9, "protein": 17, "fat": 12},
        "ingredients": ["돼지고기", "양파", "고추장", "간장", "대파"],
        "allergens": ["PORK", "SOYBEAN", "WHEAT"],
    },
    {
        "name": "간장불고기",
        "standard_serving_g": 140,
        "nutrition": {"calories": 195, "carbohydrate": 8, "protein": 18, "fat": 10},
        "ingredients": ["소고기", "양파", "간장", "배", "마늘"],
        "allergens": ["BEEF", "SOYBEAN", "WHEAT"],
    },
    {
        "name": "치킨가라아게",
        "standard_serving_g": 130,
        "nutrition": {"calories": 245, "carbohydrate": 15, "protein": 16, "fat": 13},
        "ingredients": ["닭고기", "밀가루", "전분", "간장", "마늘"],
        "allergens": ["CHICKEN", "SOYBEAN", "WHEAT"],
    },
    {
        "name": "고등어구이",
        "standard_serving_g": 90,
        "nutrition": {"calories": 210, "carbohydrate": 1, "protein": 20, "fat": 14},
        "ingredients": ["고등어", "소금", "후추"],
        "allergens": ["MACKEREL"],
    },
    {
        "name": "계란말이",
        "standard_serving_g": 90,
        "nutrition": {"calories": 165, "carbohydrate": 3, "protein": 11, "fat": 11},
        "ingredients": ["계란", "당근", "대파", "소금"],
        "allergens": ["EGGS"],
    },
    {
        "name": "두부조림",
        "standard_serving_g": 100,
        "nutrition": {"calories": 108, "carbohydrate": 5, "protein": 8, "fat": 6},
        "ingredients": ["두부", "간장", "고춧가루", "대파"],
        "allergens": ["SOYBEAN", "WHEAT"],
    },
    {
        "name": "멸치볶음",
        "standard_serving_g": 40,
        "nutrition": {"calories": 280, "carbohydrate": 18, "protein": 24, "fat": 11},
        "ingredients": ["멸치", "간장", "설탕", "참기름"],
        "allergens": ["SOYBEAN"],
    },
    {
        "name": "배추김치",
        "standard_serving_g": 40,
        "nutrition": {"calories": 32, "carbohydrate": 5, "protein": 1.6, "fat": 0.5},
        "ingredients": ["배추", "고춧가루", "마늘", "새우젓"],
        "allergens": ["SHRIMP"],
    },
    {
        "name": "오이무침",
        "standard_serving_g": 45,
        "nutrition": {"calories": 40, "carbohydrate": 6, "protein": 1.2, "fat": 1.2},
        "ingredients": ["오이", "고춧가루", "식초", "마늘"],
        "allergens": [],
    },
    {
        "name": "감자조림",
        "standard_serving_g": 70,
        "nutrition": {"calories": 115, "carbohydrate": 21, "protein": 2.5, "fat": 2},
        "ingredients": ["감자", "간장", "양파", "올리고당"],
        "allergens": ["SOYBEAN", "WHEAT"],
    },
    {
        "name": "돈까스",
        "standard_serving_g": 130,
        "nutrition": {"calories": 265, "carbohydrate": 20, "protein": 14, "fat": 14},
        "ingredients": ["돼지고기", "빵가루", "밀가루", "계란"],
        "allergens": ["PORK", "WHEAT", "EGGS"],
    },
    {
        "name": "카레라이스",
        "standard_serving_g": 260,
        "nutrition": {"calories": 170, "carbohydrate": 28, "protein": 5, "fat": 4},
        "ingredients": ["쌀", "감자", "당근", "양파", "카레가루"],
        "allergens": ["WHEAT"],
    },
    {
        "name": "어묵국",
        "standard_serving_g": 220,
        "nutrition": {"calories": 48, "carbohydrate": 5, "protein": 4, "fat": 1.4},
        "ingredients": ["어묵", "무", "대파", "간장"],
        "allergens": ["SOYBEAN", "WHEAT"],
    },
    {
        "name": "닭갈비",
        "standard_serving_g": 140,
        "nutrition": {"calories": 198, "carbohydrate": 10, "protein": 17, "fat": 10},
        "ingredients": ["닭고기", "양배추", "고추장", "고구마", "대파"],
        "allergens": ["CHICKEN", "SOYBEAN", "WHEAT"],
    },
    {
        "name": "참치마요덮밥",
        "standard_serving_g": 240,
        "nutrition": {"calories": 192, "carbohydrate": 24, "protein": 7, "fat": 8},
        "ingredients": ["쌀", "참치", "마요네즈", "양파", "김"],
        "allergens": ["EGGS"],
    },
    {
        "name": "유부장국",
        "standard_serving_g": 220,
        "nutrition": {"calories": 35, "carbohydrate": 3, "protein": 2.5, "fat": 1.8},
        "ingredients": ["유부", "다시마", "대파", "간장"],
        "allergens": ["SOYBEAN", "WHEAT"],
    },
    {
        "name": "떡볶이",
        "standard_serving_g": 120,
        "nutrition": {"calories": 176, "carbohydrate": 33, "protein": 3.5, "fat": 3.2},
        "ingredients": ["떡", "고추장", "어묵", "양배추"],
        "allergens": ["SOYBEAN", "WHEAT"],
    },
    {
        "name": "만두찜",
        "standard_serving_g": 100,
        "nutrition": {"calories": 205, "carbohydrate": 27, "protein": 7, "fat": 7},
        "ingredients": ["밀가루", "돼지고기", "부추", "양배추"],
        "allergens": ["WHEAT", "PORK", "SOYBEAN"],
    },
    {
        "name": "비빔국수",
        "standard_serving_g": 180,
        "nutrition": {"calories": 188, "carbohydrate": 34, "protein": 6, "fat": 3},
        "ingredients": ["소면", "고추장", "오이", "상추", "참기름"],
        "allergens": ["WHEAT", "SOYBEAN"],
    },
    {
        "name": "김밥",
        "standard_serving_g": 170,
        "nutrition": {"calories": 178, "carbohydrate": 29, "protein": 5.8, "fat": 4},
        "ingredients": ["쌀", "김", "계란", "단무지", "당근"],
        "allergens": ["EGGS"],
    },
    {
        "name": "순두부찌개",
        "standard_serving_g": 220,
        "nutrition": {"calories": 75, "carbohydrate": 4, "protein": 6, "fat": 4},
        "ingredients": ["순두부", "양파", "고춧가루", "바지락", "대파"],
        "allergens": ["SOYBEAN", "SHELLFISH"],
    },
    {
        "name": "불고기볶음우동",
        "standard_serving_g": 220,
        "nutrition": {"calories": 186, "carbohydrate": 26, "protein": 8, "fat": 5.5},
        "ingredients": ["우동면", "소고기", "양배추", "간장", "양파"],
        "allergens": ["WHEAT", "BEEF", "SOYBEAN"],
    },
    {
        "name": "새우볶음밥",
        "standard_serving_g": 230,
        "nutrition": {"calories": 174, "carbohydrate": 27, "protein": 7, "fat": 4.2},
        "ingredients": ["쌀", "새우", "계란", "대파", "간장"],
        "allergens": ["SHRIMP", "EGGS", "SOYBEAN"],
    },
    {
        "name": "토마토샐러드",
        "standard_serving_g": 60,
        "nutrition": {"calories": 38, "carbohydrate": 6, "protein": 1.2, "fat": 1},
        "ingredients": ["토마토", "양상추", "올리브오일", "발사믹식초"],
        "allergens": ["TOMATO"],
    },
]

LUNCH_CYCLES = [
    ["잡곡밥", "소고기미역국", "제육볶음", "감자조림", "배추김치"],
    ["쌀밥", "된장국", "간장불고기", "오이무침", "배추김치"],
    ["카레라이스", "콩나물국", "계란말이", "배추김치"],
    ["김치볶음밥", "유부장국", "치킨가라아게", "토마토샐러드"],
    ["쌀밥", "어묵국", "고등어구이", "두부조림", "배추김치"],
]

DINNER_CYCLES = [
    ["쌀밥", "순두부찌개", "돈까스", "오이무침", "배추김치"],
    ["잡곡밥", "콩나물국", "닭갈비", "멸치볶음", "배추김치"],
    ["참치마요덮밥", "유부장국", "떡볶이", "만두찜"],
    ["불고기볶음우동", "된장국", "계란말이", "토마토샐러드"],
    ["새우볶음밥", "어묵국", "비빔국수", "배추김치"],
    ["김밥", "소고기미역국", "치킨가라아게", "오이무침"],
]


def iter_july_2026_weekdays() -> Iterable[date]:
    current = date(2026, 7, 1)
    end = date(2026, 7, 31)
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def get_or_create_ingredient(session, name: str) -> Ingredient:
    ingredient = session.scalar(select(Ingredient).where(Ingredient.name == name))
    if ingredient is None:
        ingredient = Ingredient(name=name)
        session.add(ingredient)
        session.flush()
    return ingredient


def sync_menu(session, spec: dict, allergens_by_code: dict[str, Allergen]) -> Menu:
    menu = session.scalar(select(Menu).where(Menu.name == spec["name"]))
    if menu is None:
        nutrition = spec["nutrition"]
        menu = Menu(
            name=spec["name"],
            standard_serving_g=spec["standard_serving_g"],
            calories_per_100g=nutrition["calories"],
            carbohydrate_per_100g=nutrition["carbohydrate"],
            protein_per_100g=nutrition["protein"],
            fat_per_100g=nutrition["fat"],
            is_active=True,
        )
        session.add(menu)
        session.flush()

    existing_ingredient_ids = {link.ingredient_id for link in menu.ingredients}
    for ingredient_name in spec["ingredients"]:
        ingredient = get_or_create_ingredient(session, ingredient_name)
        if ingredient.id not in existing_ingredient_ids:
            menu.ingredients.append(MenuIngredient(menu_id=menu.id, ingredient_id=ingredient.id))
            existing_ingredient_ids.add(ingredient.id)

    existing_allergen_ids = {link.allergen_id for link in menu.allergens}
    for allergen_code in spec["allergens"]:
        allergen = allergens_by_code[allergen_code]
        if allergen.id not in existing_allergen_ids:
            menu.allergens.append(MenuAllergen(menu_id=menu.id, allergen_id=allergen.id))
            existing_allergen_ids.add(allergen.id)

    return menu


def sync_meal(session, *, meal_date: date, meal_type: MealType, school_name: str, menu_names: list[str], menus_by_name: dict[str, Menu]) -> Meal:
    meal = session.scalar(
        select(Meal).where(
            Meal.meal_date == meal_date,
            Meal.meal_type == meal_type.value,
            Meal.school_name == school_name,
        )
    )
    if meal is None:
        meal = Meal(meal_date=meal_date, meal_type=meal_type.value, school_name=school_name)
        session.add(meal)
        session.flush()

    desired_menu_ids = [menus_by_name[name].id for name in menu_names]
    existing_menu_ids = {link.menu_id for link in meal.meal_menu_items}
    for menu_id in desired_menu_ids:
        if menu_id not in existing_menu_ids:
            session.add(MealMenuItem(meal_id=meal.id, menu_id=menu_id))
    return meal


def main() -> None:
    school_name = "국민대학교"
    session = SessionLocal()
    try:
        allergens = session.scalars(select(Allergen)).all()
        allergens_by_code = {allergen.code: allergen for allergen in allergens}
        missing_codes = sorted(
            {
                code
                for spec in MENU_SPECS
                for code in spec["allergens"]
                if code not in allergens_by_code
            }
        )
        if missing_codes:
            raise RuntimeError(f"Missing allergen seeds: {', '.join(missing_codes)}")

        menus_by_name = {}
        created_menu_count = 0
        existing_menu_names = set(session.scalars(select(Menu.name)).all())
        for spec in MENU_SPECS:
            if spec["name"] not in existing_menu_names:
                created_menu_count += 1
            menus_by_name[spec["name"]] = sync_menu(session, spec, allergens_by_code)
        session.flush()

        created_meal_count = 0
        for index, meal_date in enumerate(iter_july_2026_weekdays()):
            lunch_names = LUNCH_CYCLES[index % len(LUNCH_CYCLES)]
            dinner_names = DINNER_CYCLES[index % len(DINNER_CYCLES)]
            if session.scalar(select(Meal.id).where(Meal.meal_date == meal_date, Meal.meal_type == MealType.LUNCH.value, Meal.school_name == school_name)) is None:
                created_meal_count += 1
            sync_meal(
                session,
                meal_date=meal_date,
                meal_type=MealType.LUNCH,
                school_name=school_name,
                menu_names=lunch_names,
                menus_by_name=menus_by_name,
            )
            if session.scalar(select(Meal.id).where(Meal.meal_date == meal_date, Meal.meal_type == MealType.DINNER.value, Meal.school_name == school_name)) is None:
                created_meal_count += 1
            sync_meal(
                session,
                meal_date=meal_date,
                meal_type=MealType.DINNER,
                school_name=school_name,
                menu_names=dinner_names,
                menus_by_name=menus_by_name,
            )

        session.commit()
        weekday_count = sum(1 for _ in iter_july_2026_weekdays())
        print(
            f"Seeded July 2026 meals for {school_name}: "
            f"{weekday_count} weekdays, {created_menu_count} new menus, {created_meal_count} new meals."
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
