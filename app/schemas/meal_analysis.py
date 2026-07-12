from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import AnalysisType, ConsumptionLevel


class MealAnalyzeRequest(BaseModel):
    analysis_type: AnalysisType


class MealReanalyzeRequest(BaseModel):
    analysis_type: AnalysisType
    reason: str = Field(min_length=1, max_length=255)


class MealAnalysisItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_record_id: int
    meal_menu_item_id: int
    menu_name: str
    consumed_ratio: float
    consumption_level: ConsumptionLevel
    confidence: float | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class MealAnalysisResponse(BaseModel):
    meal_record_id: int
    analysis_note: str
    items: list[MealAnalysisItemResponse]
