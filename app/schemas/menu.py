from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NutritionPer100gSchema(BaseModel):
    calories_kcal: float = Field(ge=0)
    carbohydrate_g: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MenuCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    standard_serving_g: float = Field(gt=0)
    nutrition_per_100g: NutritionPer100gSchema
    ingredients: list[str] = Field(default_factory=list)
    allergen_codes: list[str] = Field(default_factory=list)


class MenuUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    standard_serving_g: float | None = Field(default=None, gt=0)
    nutrition_per_100g: NutritionPer100gSchema | None = None
    ingredients: list[str] | None = None
    allergen_codes: list[str] | None = None
    is_active: bool | None = None


class IngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    standard_serving_g: float
    calories_per_100g: float
    carbohydrate_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    ingredients: list[str]
    allergen_codes: list[str]


class MenuListResponse(BaseModel):
    items: list[MenuResponse]
    total: int
