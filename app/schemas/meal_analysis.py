from pydantic import BaseModel, ConfigDict, Field

from app.schemas.meal_record import MealItemRecordResponse
from app.utils.enums import AnalysisType


class VisionItemResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    consumed_ratio: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    note: str | None = None


class VisionAnalysisResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[VisionItemResultSchema] = Field(min_length=1)
    analysis_note: str = "식전·식후 이미지 비교 결과"


class ComparedFoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_name: str
    consumed_ratio: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    note: str | None = None


class VisionImageComparisonResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_consumed_ratio: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    items: list[ComparedFoodItem] = Field(min_length=1)
    summary: str
    warnings: list[str] = Field(default_factory=list)
    analysis_possible: bool = True
    same_meal: bool = True
    analysis_impossible_reason: str | None = None


class ImageComparisonAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_consumed_ratio: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    items: list[ComparedFoodItem] = Field(min_length=1)
    summary: str
    warnings: list[str] = Field(default_factory=list)


class MealAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_record_id: int
    analysis_type: AnalysisType
    analysis_note: str
    items: list[MealItemRecordResponse]
