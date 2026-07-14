from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import UserRole


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    login_id: str | None = Field(default=None, min_length=3, max_length=50)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    name: str
    student_number: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
