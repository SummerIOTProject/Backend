from fastapi import APIRouter, Depends

from app.api.dependencies import get_allergen_service
from app.schemas.allergen import AllergenResponse, MyAllergenListResponse, UpdateMyAllergiesRequest
from app.schemas.common import CommonResponse
from app.services.allergen_service import AllergenService

router = APIRouter(prefix="/allergens", tags=["Allergens"])


@router.get("", response_model=CommonResponse[list[AllergenResponse]])
def list_allergens(service: AllergenService = Depends(get_allergen_service)):
    return CommonResponse(message="알레르기 태그 목록입니다.", data=[AllergenResponse.model_validate(item) for item in service.list_allergens()])
