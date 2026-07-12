from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class RfidCardCreateRequest(BaseModel):
    user_id: int
    uid: str = Field(min_length=1, max_length=100)


class RfidScanRequest(BaseModel):
    uid: str = Field(min_length=1, max_length=100)


class RfidCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    uid: str
    is_active: bool
    registered_at: datetime


class RfidScanResponse(BaseModel):
    card: RfidCardResponse
    user: UserResponse
