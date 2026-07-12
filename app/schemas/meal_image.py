from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.utils.enums import ImageType


class MealImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_record_id: int
    image_type: ImageType
    image_url: str
    original_filename: str | None
    content_type: str | None
    uploaded_at: datetime


class MealImageListResponse(BaseModel):
    items: list[MealImageResponse]
    total: int
