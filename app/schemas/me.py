from pydantic import BaseModel

from app.schemas.meal_record import MealRecordDetailResponse, MealRecordResponse
from app.schemas.recommendation import ServingRecommendationResponse
from app.schemas.rfid import RfidCardResponse
from app.schemas.user import UserUpdateRequest


class MeUpdateRequest(UserUpdateRequest):
    role: str | None = None
    is_active: bool | None = None


class MyRfidCardListResponse(BaseModel):
    items: list[RfidCardResponse]
    total: int


class MyRfidCardCreateRequest(BaseModel):
    uid: str


class MyMealRecordListResponse(BaseModel):
    items: list[MealRecordResponse]
    total: int


class ConsumptionSummaryResponse(BaseModel):
    user_id: int
    analysis_count: int
    average_consumed_ratio: float
    average_leftover_ratio: float


class MyMealRecordDetailResponse(MealRecordDetailResponse):
    pass


class MyRecommendationResponse(ServingRecommendationResponse):
    pass
