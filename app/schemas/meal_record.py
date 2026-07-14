from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.meal import MealDetailResponse
from app.schemas.meal_image import MealImageResponse
from app.utils.enums import ConsumptionLevel, MealRecordStatus


class MealRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    meal_id: int
    status: MealRecordStatus
    started_at: datetime
    completed_at: datetime | None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ItemNutritionResponse(BaseModel):
    estimated_consumed_g: float
    calories_kcal: float
    carbohydrate_g: float
    protein_g: float
    fat_g: float
    is_estimated: bool


class MealItemRecordResponse(BaseModel):
    id: int
    meal_record_id: int
    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    consumed_ratio: float
    consumed_percent: float
    consumption_level: ConsumptionLevel
    confidence: float | None
    is_corrected: bool
    corrected_at: datetime | None
    corrected_by: int | None
    note: str | None
    analysis_type: str
    nutrition: ItemNutritionResponse
    created_at: datetime
    updated_at: datetime


class MealRecordDetailResponse(MealRecordResponse):
    meal: MealDetailResponse
    images: list[MealImageResponse]
    item_records: list[MealItemRecordResponse]


class RecentMealRecordListResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[MealRecordDetailResponse]
    total: int


class CorrectConsumedRatioRequest(BaseModel):
    consumed_ratio: float = Field(ge=0.0, le=1.0)
