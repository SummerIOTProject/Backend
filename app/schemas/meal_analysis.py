from pydantic import BaseModel, ConfigDict, Field

from app.schemas.meal_record import MealItemRecordResponse
from app.utils.enums import AnalysisType

class VisionItemResultSchema(BaseModel):
    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    consumed_ratio: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    note: str | None = None


class VisionAnalysisResultSchema(BaseModel):
    items: list[VisionItemResultSchema]


class MealAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_record_id: int
    analysis_type: AnalysisType
    analysis_note: str
    items: list[MealItemRecordResponse]
