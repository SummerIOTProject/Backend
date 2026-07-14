from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    get_allergen_service,
    get_analysis_service,
    get_meal_record_service,
    get_nutrition_service,
    get_recommendation_service,
    get_rfid_service,
    get_user_service,
)
from app.api.mappers.response_mappers import to_meal_item_record_response, to_meal_record_response, to_recommendation_response
from app.core.security import get_current_user
from app.schemas.allergen import AllergenResponse, MyAllergenListResponse, UpdateMyAllergiesRequest
from app.schemas.common import CommonResponse
from app.schemas.meal_record import CorrectConsumedRatioRequest, MealItemRecordResponse, MealRecordDetailResponse, RecentMealRecordListResponse
from app.schemas.recommendation import RecommendationItemResponse, RecommendationListResponse
from app.schemas.rfid import RfidCardCreateRequest, RfidCardResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.allergen_service import AllergenService
from app.services.analysis_service import AnalysisService
from app.services.meal_record_service import MealRecordService
from app.services.nutrition_service import NutritionService
from app.services.recommendation_service import RecommendationService
from app.services.rfid_service import RfidService
from app.services.user_service import UserService

router = APIRouter(prefix="/me", tags=["Me"])


@router.get("", response_model=CommonResponse[UserResponse])
def get_me(current_user=Depends(get_current_user)):
    return CommonResponse(message="내 정보입니다.", data=UserResponse.model_validate(current_user))


@router.patch("", response_model=CommonResponse[UserResponse])
def update_me(request: UserUpdateRequest, current_user=Depends(get_current_user), service: UserService = Depends(get_user_service)):
    user = service.update_me(current_user.id, request)
    return CommonResponse(message="내 정보가 수정되었습니다.", data=UserResponse.model_validate(user))


@router.get("/allergens", response_model=CommonResponse[MyAllergenListResponse])
def get_my_allergies(current_user=Depends(get_current_user), service: AllergenService = Depends(get_allergen_service)):
    items = service.get_my_allergies(current_user.id)
    return CommonResponse(message="내 알레르기 목록입니다.", data=MyAllergenListResponse(items=[AllergenResponse.model_validate(item) for item in items], total=len(items)))


@router.put("/allergens", response_model=CommonResponse[MyAllergenListResponse])
def replace_my_allergies(request: UpdateMyAllergiesRequest, current_user=Depends(get_current_user), service: AllergenService = Depends(get_allergen_service)):
    items = service.replace_my_allergies(current_user.id, request.allergen_codes)
    return CommonResponse(message="알레르기 정보가 수정되었습니다.", data=MyAllergenListResponse(items=[AllergenResponse.model_validate(item) for item in items], total=len(items)))


@router.post("/rfid-cards", response_model=CommonResponse[RfidCardResponse], status_code=201)
def register_my_rfid_card(request: RfidCardCreateRequest, current_user=Depends(get_current_user), service: RfidService = Depends(get_rfid_service)):
    card = service.register_my_card(current_user.id, request.uid)
    return CommonResponse(message="RFID 카드가 등록되었습니다.", data=RfidCardResponse.model_validate(card))


@router.get("/rfid-cards", response_model=CommonResponse[list[RfidCardResponse]])
def list_my_rfid_cards(current_user=Depends(get_current_user), service: RfidService = Depends(get_rfid_service)):
    cards = service.list_my_cards(current_user.id)
    return CommonResponse(message="내 RFID 카드 목록입니다.", data=[RfidCardResponse.model_validate(card) for card in cards])


@router.get("/meal-records/recent", response_model=CommonResponse[RecentMealRecordListResponse])
def get_recent_records(
    days: int = Query(default=5, ge=1, le=30),
    current_user=Depends(get_current_user),
    service: MealRecordService = Depends(get_meal_record_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    start_date, end_date, records = service.list_recent(current_user.id, days)
    return CommonResponse(
        message="최근 식사 기록입니다.",
        data=RecentMealRecordListResponse(
            start_date=start_date,
            end_date=end_date,
            items=[to_meal_record_response(record, nutrition_service) for record in records],
            total=len(records),
        ),
    )


@router.patch("/meal-item-records/{meal_item_record_id}/consumed-ratio", response_model=CommonResponse[MealItemRecordResponse])
def correct_consumed_ratio(
    meal_item_record_id: int,
    request: CorrectConsumedRatioRequest,
    current_user=Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    item = service.correct_consumed_ratio(meal_item_record_id, current_user.id, request.consumed_ratio)
    return CommonResponse(message="섭취율이 보정되었습니다.", data=to_meal_item_record_response(item, nutrition_service))


@router.get("/recommendations", response_model=CommonResponse[RecommendationListResponse])
def get_my_recommendations(
    meal_id: int,
    current_user=Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
):
    items = service.generate_for_meal(user_id=current_user.id, meal_id=meal_id)
    return CommonResponse(message="배식 추천 결과입니다.", data=RecommendationListResponse(meal_id=meal_id, items=[to_recommendation_response(item) for item in items]))


@router.patch("/rfid-cards/{card_id}/deactivate", response_model=CommonResponse[RfidCardResponse])
def deactivate_my_rfid_card(card_id: int, current_user=Depends(get_current_user), service: RfidService = Depends(get_rfid_service)):
    card = service.deactivate_my_card(current_user.id, card_id)
    return CommonResponse(message="RFID 카드가 비활성화되었습니다.", data=RfidCardResponse.model_validate(card))
