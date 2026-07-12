from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    student_number: str = Field(min_length=1, max_length=30)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    student_number: str | None = Field(default=None, min_length=1, max_length=30)
    email: EmailStr | None = None
    is_active: bool | None = None
    role: str | None = Field(default=None, min_length=1, max_length=20)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    student_number: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
