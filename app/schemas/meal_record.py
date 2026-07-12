from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.meal import MealResponse
from app.schemas.meal_analysis import MealAnalysisItemResponse
from app.schemas.meal_image import MealImageResponse
from app.schemas.user import UserResponse
from app.utils.enums import MealRecordStatus


class MealRecordCreateRequest(BaseModel):
    user_id: int
    meal_id: int


class MealRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    meal_id: int
    status: MealRecordStatus
    started_at: datetime
    completed_at: datetime | None
    failure_reason: str | None


class MealRecordDetailResponse(MealRecordResponse):
    user: UserResponse
    meal: MealResponse
    images: list[MealImageResponse]
    analyses: list[MealAnalysisItemResponse]
