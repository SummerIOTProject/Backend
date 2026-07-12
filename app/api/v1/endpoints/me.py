from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_meal_record_service, get_recommendation_service, get_rfid_service, get_user_service
from app.core.security import require_active_user
from app.schemas.auth import CurrentUserResponse
from app.schemas.common import CommonResponse
from app.schemas.me import ConsumptionSummaryResponse, MyMealRecordListResponse, MyRfidCardCreateRequest, MyRfidCardListResponse
from app.schemas.meal_record import MealRecordDetailResponse
from app.schemas.recommendation import ServingRecommendationItemResponse, ServingRecommendationResponse
from app.schemas.rfid import RfidCardCreateRequest, RfidCardResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.meal_record_service import MealRecordService
from app.services.recommendation_service import RecommendationService
from app.services.rfid_service import RfidService
from app.services.user_service import UserService

router = APIRouter(prefix="/me", tags=["Me"])


def _to_current_user_response(user) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user.id,
        name=user.name,
        student_number=user.student_number,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.get(
    "",
    summary="내 정보 조회",
    response_model=CommonResponse[CurrentUserResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_profile(current_user=Depends(require_active_user)):
    return CommonResponse(success=True, message="내 정보입니다.", data=_to_current_user_response(current_user))


@router.patch(
    "",
    summary="내 정보 수정",
    response_model=CommonResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
def update_my_profile(
    request: UserUpdateRequest,
    service: UserService = Depends(get_user_service),
    current_user=Depends(require_active_user),
):
    payload = request.model_copy(update={"role": None, "is_active": None})
    user = service.update_user(current_user.id, payload)
    return CommonResponse(success=True, message="내 정보가 수정되었습니다.", data=UserResponse.model_validate(user))


@router.get(
    "/rfid-cards",
    summary="내 RFID 카드 조회",
    response_model=CommonResponse[MyRfidCardListResponse],
    status_code=status.HTTP_200_OK,
)
def list_my_rfid_cards(service: RfidService = Depends(get_rfid_service), current_user=Depends(require_active_user)):
    cards = service.list_user_cards(current_user.id)
    data = MyRfidCardListResponse(items=[RfidCardResponse.model_validate(card) for card in cards], total=len(cards))
    return CommonResponse(success=True, message="내 RFID 카드 목록입니다.", data=data)


@router.post(
    "/rfid-cards",
    summary="내 RFID 카드 연결",
    response_model=CommonResponse[RfidCardResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_my_rfid_card(
    request: MyRfidCardCreateRequest,
    service: RfidService = Depends(get_rfid_service),
    current_user=Depends(require_active_user),
):
    request = request.model_copy(update={"user_id": current_user.id})
    card = service.register_card(RfidCardCreateRequest(user_id=current_user.id, uid=request.uid))
    return CommonResponse(success=True, message="RFID 카드가 연결되었습니다.", data=RfidCardResponse.model_validate(card))


@router.get(
    "/meal-records",
    summary="내 식사 기록 목록",
    response_model=CommonResponse[MyMealRecordListResponse],
    status_code=status.HTTP_200_OK,
)
def list_my_meal_records(
    service: MealRecordService = Depends(get_meal_record_service),
    current_user=Depends(require_active_user),
):
    records = service.list_user_records(current_user.id)
    data = MyMealRecordListResponse(items=records, total=len(records))
    return CommonResponse(success=True, message="내 식사 기록 목록입니다.", data=data)


@router.get(
    "/meal-records/{record_id}",
    summary="내 식사 기록 상세",
    response_model=CommonResponse[MealRecordDetailResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_meal_record(
    record_id: int,
    service: MealRecordService = Depends(get_meal_record_service),
    current_user=Depends(require_active_user),
):
    record = service.assert_record_owner(record_id, current_user.id)
    return CommonResponse(
        success=True,
        message="내 식사 기록 상세입니다.",
        data=MealRecordDetailResponse.model_validate(record),
    )


@router.get(
    "/recommendations",
    summary="내 배식 추천 조회",
    response_model=CommonResponse[ServingRecommendationResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_recommendations(
    meal_id: int = Query(...),
    service: RecommendationService = Depends(get_recommendation_service),
    current_user=Depends(require_active_user),
):
    items = service.get_recommendations_for_meal(user_id=current_user.id, meal_id=meal_id)
    data = ServingRecommendationResponse(
        user_id=current_user.id,
        meal_id=meal_id,
        items=[
            ServingRecommendationItemResponse(
                id=item.id,
                meal_menu_item_id=item.meal_menu_item_id,
                menu_name=item.meal_menu_item.name,
                recommendation_level=item.recommendation_level,
                average_consumed_ratio=item.average_consumed_ratio,
                reason=item.reason,
                created_at=item.created_at,
            )
            for item in items
        ],
    )
    return CommonResponse(success=True, message="내 배식 추천 결과입니다.", data=data)


@router.get(
    "/recommendations/history",
    summary="내 배식 추천 이력 조회",
    response_model=CommonResponse[ServingRecommendationResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_recommendation_history(
    service: RecommendationService = Depends(get_recommendation_service),
    current_user=Depends(require_active_user),
):
    items = service.list_history(current_user.id)
    data = ServingRecommendationResponse(
        user_id=current_user.id,
        meal_id=None,
        items=[
            ServingRecommendationItemResponse(
                id=item.id,
                meal_menu_item_id=item.meal_menu_item_id,
                menu_name=item.meal_menu_item.name,
                recommendation_level=item.recommendation_level,
                average_consumed_ratio=item.average_consumed_ratio,
                reason=item.reason,
                created_at=item.created_at,
            )
            for item in items
        ],
    )
    return CommonResponse(success=True, message="내 배식 추천 이력입니다.", data=data)


@router.get(
    "/consumption-summary",
    summary="내 섭취 경향 조회",
    response_model=CommonResponse[ConsumptionSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_consumption_summary(
    service: RecommendationService = Depends(get_recommendation_service),
    current_user=Depends(require_active_user),
):
    summary = service.get_consumption_summary(current_user.id)
    return CommonResponse(
        success=True,
        message="내 섭취 경향 요약입니다.",
        data=ConsumptionSummaryResponse.model_validate(summary),
    )
