from fastapi import APIRouter, Depends, status

from app.api.mappers.response_mappers import to_meal_response
from app.api.dependencies import get_meal_service
from app.core.security import get_current_user, require_admin
from app.schemas.common import CommonResponse
from app.schemas.meal import MealCreateRequest, MealDetailResponse, MealListResponse, MealMenuItemResponse, NutritionPer100gSchema
from app.services.meal_service import MealService

router = APIRouter(tags=["Meals"])


@router.post("/admin/meals", response_model=CommonResponse[MealDetailResponse], status_code=status.HTTP_201_CREATED)
def create_meal(request: MealCreateRequest, _: object = Depends(require_admin), service: MealService = Depends(get_meal_service)):
    return CommonResponse(message="급식이 등록되었습니다.", data=to_meal_response(service.create_meal(request)))


@router.get("/meals/today", response_model=CommonResponse[MealListResponse])
def get_today_meals(service: MealService = Depends(get_meal_service)):
    items = service.get_today_meals()
    return CommonResponse(message="오늘 급식 목록입니다.", data=MealListResponse(items=[to_meal_response(item) for item in items], total=len(items)))


@router.get("/meals/{meal_id}", response_model=CommonResponse[MealDetailResponse])
def get_meal(meal_id: int, _: object = Depends(get_current_user), service: MealService = Depends(get_meal_service)):
    return CommonResponse(message="급식 상세입니다.", data=to_meal_response(service.get_meal(meal_id)))
