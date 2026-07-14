from pydantic import BaseModel, ConfigDict, Field


class AllergenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_ko: str
    display_number: int
    description: str | None
    is_active: bool


class UpdateMyAllergiesRequest(BaseModel):
    allergen_codes: list[str] = Field(default_factory=list)


class MyAllergenListResponse(BaseModel):
    items: list[AllergenResponse]
    total: int
