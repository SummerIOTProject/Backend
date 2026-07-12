from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.utils.enums import RecommendationLevel


class ServingRecommendationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_menu_item_id: int
    menu_name: str
    recommendation_level: RecommendationLevel
    average_consumed_ratio: float | None
    reason: str
    created_at: datetime


class ServingRecommendationResponse(BaseModel):
    user_id: int
    meal_id: int | None = None
    items: list[ServingRecommendationItemResponse]
