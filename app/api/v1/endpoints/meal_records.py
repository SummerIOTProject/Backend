from fastapi import APIRouter, Depends

from app.api.mappers.response_mappers import to_meal_record_response
from app.api.dependencies import get_meal_record_service, get_nutrition_service
from app.core.security import get_current_user, require_admin
from app.schemas.common import CommonResponse
from app.schemas.meal_record import MealRecordDetailResponse
from app.services.meal_record_service import MealRecordService
from app.services.nutrition_service import NutritionService

router = APIRouter(tags=["Meal Records"])


@router.get("/me/meal-records/{meal_record_id}", response_model=CommonResponse[MealRecordDetailResponse])
def get_my_record(
    meal_record_id: int,
    current_user=Depends(get_current_user),
    service: MealRecordService = Depends(get_meal_record_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    record = service.assert_owner(meal_record_id, current_user.id)
    return CommonResponse(message="식사 기록 상세입니다.", data=to_meal_record_response(record, nutrition_service))


@router.get("/admin/meal-records", response_model=CommonResponse[list[MealRecordDetailResponse]])
def list_all_records(
    _: object = Depends(require_admin),
    service: MealRecordService = Depends(get_meal_record_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    items = service.list_all()
    return CommonResponse(message="전체 식사 기록 목록입니다.", data=[to_meal_record_response(item, nutrition_service) for item in items])
