from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import MealType


class MealMenuItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=30)
    tray_section: int | None = Field(default=None, ge=1)
    display_order: int = Field(ge=1)


class MealCreateRequest(BaseModel):
    meal_date: date
    meal_type: MealType
    school_name: str = Field(min_length=1, max_length=100)
    menu_items: list[MealMenuItemCreateRequest]


class MealUpdateRequest(BaseModel):
    meal_date: date | None = None
    meal_type: MealType | None = None
    school_name: str | None = Field(default=None, min_length=1, max_length=100)
    menu_items: list[MealMenuItemCreateRequest] | None = None


class MealMenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_id: int
    name: str
    category: str | None
    tray_section: int | None
    display_order: int


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_date: date
    meal_type: MealType
    school_name: str
    created_at: datetime
    updated_at: datetime
    menu_items: list[MealMenuItemResponse]


class MealListResponse(BaseModel):
    items: list[MealResponse]
    total: int
