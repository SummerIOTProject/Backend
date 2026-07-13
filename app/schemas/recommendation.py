from pydantic import BaseModel, ConfigDict

from app.utils.enums import RecommendationLevel


class RecommendationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_id: int
    meal_menu_item_id: int
    menu_id: int
    menu_name: str
    standard_serving_g: float
    recommendation_level: RecommendationLevel
    recommended_serving_ratio: float
    recommended_serving_g: float
    recent_average_consumed_ratio: float | None
    sample_count: int
    reason: str


class RecommendationListResponse(BaseModel):
    meal_id: int
    items: list[RecommendationItemResponse]
