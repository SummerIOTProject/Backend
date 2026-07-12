from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorDetailSchema(BaseModel):
    code: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorDetailSchema


class CommonResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None


class PaginationMeta(BaseModel):
    total: int


class HealthResponse(BaseModel):
    status: str


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    registered_user_count: int
    meal_record_count: int
    completed_analysis_count: int
    average_consumed_ratio: float
    average_leftover_ratio: float


class LeftoverSummaryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_name: str
    average_consumed_ratio: float
    average_leftover_ratio: float
    analysis_count: int


class LeftoverSummaryResponse(BaseModel):
    start_date: str
    end_date: str
    items: list[LeftoverSummaryItemResponse]


class AdminMealRecordListResponse(BaseModel):
    items: list
    total: int
