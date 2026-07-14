from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.menu import NutritionPer100gSchema
from app.utils.enums import MealType


class MealCreateRequest(BaseModel):
    meal_date: date
    meal_type: MealType
    school_name: str = Field(min_length=1, max_length=100)
    menu_ids: list[int] = Field(min_length=1)


class MealMenuItemResponse(BaseModel):
    meal_menu_item_id: int
    menu_id: int
    name: str
    standard_serving_g: float
    nutrition_per_100g: NutritionPer100gSchema
    ingredients: list[str]
    allergens: list[str]


class MealDetailResponse(BaseModel):
    id: int
    meal_date: date
    meal_type: MealType
    school_name: str
    created_at: datetime
    updated_at: datetime
    menu_items: list[MealMenuItemResponse]


class MealListResponse(BaseModel):
    items: list[MealDetailResponse]
    total: int
