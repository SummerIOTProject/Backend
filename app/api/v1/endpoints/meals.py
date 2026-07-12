from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_meal_service
from app.core.security import require_active_user, require_admin
from app.schemas.common import CommonResponse
from app.schemas.meal import MealCreateRequest, MealListResponse, MealResponse, MealUpdateRequest
from app.services.meal_service import MealService

router = APIRouter(prefix="/meals", tags=["Meals"])


@router.post(
    "",
    summary="식단 등록",
    description="식단과 메뉴를 함께 등록합니다.",
    response_model=CommonResponse[MealResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_meal(
    request: MealCreateRequest,
    service: MealService = Depends(get_meal_service),
    _: object = Depends(require_admin),
):
    meal = service.create_meal(request)
    return CommonResponse(success=True, message="식단이 등록되었습니다.", data=MealResponse.model_validate(meal))


@router.get(
    "",
    summary="식단 목록 조회",
    description="등록된 식단 목록을 조회합니다.",
    response_model=CommonResponse[MealListResponse],
    status_code=status.HTTP_200_OK,
)
def list_meals(service: MealService = Depends(get_meal_service)):
    meals = service.list_meals()
    data = MealListResponse(items=[MealResponse.model_validate(meal) for meal in meals], total=len(meals))
    return CommonResponse(success=True, message="식단 목록입니다.", data=data)


@router.get(
    "/today",
    summary="오늘 식단 조회",
    description="오늘 날짜의 식단 목록을 조회합니다.",
    response_model=CommonResponse[MealListResponse],
    status_code=status.HTTP_200_OK,
)
def get_today_meals(service: MealService = Depends(get_meal_service)):
    meals = service.get_today_meals()
    data = MealListResponse(items=[MealResponse.model_validate(meal) for meal in meals], total=len(meals))
    return CommonResponse(success=True, message="오늘 식단 목록입니다.", data=data)


@router.get(
    "/{meal_id}",
    summary="식단 상세 조회",
    description="식단 상세 정보를 조회합니다.",
    response_model=CommonResponse[MealResponse],
    status_code=status.HTTP_200_OK,
)
def get_meal(
    meal_id: int,
    service: MealService = Depends(get_meal_service),
    _: object = Depends(require_active_user),
):
    meal = service.get_meal(meal_id)
    return CommonResponse(success=True, message="식단 상세 정보입니다.", data=MealResponse.model_validate(meal))


@router.patch(
    "/{meal_id}",
    summary="식단 수정",
    description="식단과 메뉴를 수정합니다.",
    response_model=CommonResponse[MealResponse],
    status_code=status.HTTP_200_OK,
)
def update_meal(
    meal_id: int,
    request: MealUpdateRequest,
    service: MealService = Depends(get_meal_service),
    _: object = Depends(require_admin),
):
    meal = service.update_meal(meal_id, request)
    return CommonResponse(success=True, message="식단이 수정되었습니다.", data=MealResponse.model_validate(meal))


@router.delete(
    "/{meal_id}",
    summary="식단 삭제",
    description="식단을 삭제합니다.",
    response_model=CommonResponse[None],
    status_code=status.HTTP_200_OK,
)
def delete_meal(
    meal_id: int,
    service: MealService = Depends(get_meal_service),
    _: object = Depends(require_admin),
):
    service.delete_meal(meal_id)
    return CommonResponse(success=True, message="식단이 삭제되었습니다.", data=None)
