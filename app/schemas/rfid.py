from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.meal import MealDetailResponse
from app.utils.enums import MealType


class RfidCardCreateRequest(BaseModel):
    uid: str = Field(min_length=1, max_length=100)


class RfidCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    uid: str
    is_active: bool
    registered_at: datetime


class DeviceRfidScanRequest(BaseModel):
    uid: str = Field(min_length=1, max_length=100)
    meal_type: MealType


class DeviceMealRecordCreateRequest(BaseModel):
    rfid_uid: str = Field(min_length=1, max_length=100)
    meal_id: int


class RestrictedMenuResponse(BaseModel):
    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    matched_allergens: list[str]
    is_restricted: bool


class DeviceUserResponse(BaseModel):
    user_id: int
    login_id: str
    name: str
    student_number: str


class DeviceMealResponse(MealDetailResponse):
    pass


class DeviceMenuGuidanceResponse(BaseModel):
    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    allergens: list[str]
    matched_allergens: list[str]
    is_restricted: bool
    recommendation_level: str
    recommended_serving_g: float


class DeviceRfidScanResponse(BaseModel):
    user: DeviceUserResponse
    meal: DeviceMealResponse
    menu_guidance: list[DeviceMenuGuidanceResponse]
