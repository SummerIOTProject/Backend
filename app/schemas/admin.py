from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserResponse


class AdminUserListResponse(BaseModel):
    items: list[UserResponse]
    page: int
    size: int
    total: int


class AdminDashboardResponse(BaseModel):
    date: date
    active_user_count: int
    meal_record_count: int
    completed_analysis_count: int
    failed_analysis_count: int
    average_consumed_ratio: float
    average_leftover_ratio: float


class LeftoverSummaryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_id: int
    menu_name: str
    analysis_count: int
    average_consumed_ratio: float
    average_leftover_ratio: float
