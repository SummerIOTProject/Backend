from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_meal_record_service
from app.core.security import require_active_user, require_admin
from app.schemas.common import CommonResponse
from app.schemas.meal_record import MealRecordCreateRequest, MealRecordDetailResponse, MealRecordResponse
from app.services.meal_record_service import MealRecordService

router = APIRouter(tags=["Meal Records"])


@router.post(
    "/meal-records",
    summary="식사 기록 생성",
    description="사용자와 식단 기준으로 식사 기록을 생성합니다.",
    response_model=CommonResponse[MealRecordDetailResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_meal_record(request: MealRecordCreateRequest, service: MealRecordService = Depends(get_meal_record_service)):
    record = service.create_record(request)
    return CommonResponse(success=True, message="식사 기록이 생성되었습니다.", data=MealRecordDetailResponse.model_validate(record))


@router.get(
    "/meal-records/{meal_record_id}",
    summary="식사 기록 상세 조회",
    description="식사 기록 상세 정보를 조회합니다.",
    response_model=CommonResponse[MealRecordDetailResponse],
    status_code=status.HTTP_200_OK,
)
def get_meal_record(meal_record_id: int, service: MealRecordService = Depends(get_meal_record_service)):
    record = service.get_record_detail(meal_record_id)
    return CommonResponse(success=True, message="식사 기록 상세 정보입니다.", data=MealRecordDetailResponse.model_validate(record))


@router.get(
    "/users/{user_id}/meal-records",
    summary="사용자 식사 기록 조회",
    description="특정 사용자의 식사 기록 목록을 조회합니다.",
    response_model=CommonResponse[list[MealRecordResponse]],
    status_code=status.HTTP_200_OK,
)
def list_user_meal_records(
    user_id: int,
    service: MealRecordService = Depends(get_meal_record_service),
    _: object = Depends(require_admin),
):
    records = service.list_user_records(user_id)
    return CommonResponse(
        success=True,
        message="사용자 식사 기록 목록입니다.",
        data=[MealRecordResponse.model_validate(record) for record in records],
    )


@router.delete(
    "/meal-records/{meal_record_id}",
    summary="식사 기록 삭제",
    description="식사 기록을 삭제합니다.",
    response_model=CommonResponse[None],
    status_code=status.HTTP_200_OK,
)
def delete_meal_record(meal_record_id: int, service: MealRecordService = Depends(get_meal_record_service)):
    service.delete_record(meal_record_id)
    return CommonResponse(success=True, message="식사 기록이 삭제되었습니다.", data=None)


@router.get(
    "/admin/meal-records",
    summary="전체 식사 기록 조회",
    description="관리자가 전체 식사 기록을 조회합니다.",
    response_model=CommonResponse[list[MealRecordResponse]],
    status_code=status.HTTP_200_OK,
)
def list_all_meal_records(
    service: MealRecordService = Depends(get_meal_record_service),
    _: object = Depends(require_admin),
):
    records = service.list_all_records()
    return CommonResponse(
        success=True,
        message="전체 식사 기록 목록입니다.",
        data=[MealRecordResponse.model_validate(record) for record in records],
    )
