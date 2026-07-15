from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

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
    name: str
    student_number: str


class DeviceMealResponse(BaseModel):
    id: int
    meal_date: date
    meal_type: MealType


class DeviceMenuGuidanceResponse(BaseModel):
    menu_id: int
    menu_name: str
    matched_allergens: list[str]
    is_restricted: bool
    recommendation_level: str
    recommended_serving_g: float


class DeviceRfidScanResponse(BaseModel):
    user: DeviceUserResponse
    meal: DeviceMealResponse
    menu_guidance: list[DeviceMenuGuidanceResponse]
