from typing import Generic, TypeVar

from pydantic import BaseModel

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
    message: str = "요청이 성공했습니다."
    data: T | None = None


class HealthResponse(BaseModel):
    status: str
