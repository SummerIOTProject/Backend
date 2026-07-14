from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.utils.enums import ImageType


class MealImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_record_id: int
    image_type: ImageType
    image_url: str
    mime_type: str
    file_size: int
    created_at: datetime


class MealImageUploadResponse(BaseModel):
    image_id: int
    image_url: str
