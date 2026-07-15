from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_meal_record_service, get_meal_service, get_recommendation_service, get_rfid_service
from app.api.mappers.response_mappers import to_device_scan_response, to_meal_record_response
from app.core.security import require_device_key
from app.schemas.common import CommonResponse
from app.schemas.meal_record import MealRecordDetailResponse
from app.schemas.rfid import DeviceMealRecordCreateRequest, DeviceRfidScanRequest, DeviceRfidScanResponse
from app.services.meal_record_service import MealRecordService
from app.services.meal_service import MealService
from app.services.nutrition_service import NutritionService
from app.services.recommendation_service import RecommendationService
from app.services.rfid_service import RfidService

router = APIRouter(prefix="/device", tags=["Device"], dependencies=[Depends(require_device_key)])


@router.post("/rfid/scan", response_model=CommonResponse[DeviceRfidScanResponse])
def scan_rfid(
    request: DeviceRfidScanRequest,
    rfid_service: RfidService = Depends(get_rfid_service),
    meal_service: MealService = Depends(get_meal_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    card = rfid_service.get_scan_ready_card_by_uid(request.uid)
    meal = meal_service.get_today_meal_by_type(request.meal_type)
    guidance = []
    recommendations = recommendation_service.generate_for_meal(user_id=card.user_id, meal_id=meal.id)
    recommendation_map = {item.meal_menu_item_id: item for item in recommendations}
    user_allergens = {item.allergen.code: item.allergen.name_ko for item in card.user.allergies}
    for meal_menu_item in meal.meal_menu_items:
        menu_allergen_codes = {link.allergen.code for link in meal_menu_item.menu.allergens}
        matched_codes = sorted(user_allergens.keys() & menu_allergen_codes)
        matched = [user_allergens[code] for code in matched_codes]
        rec = recommendation_map[meal_menu_item.id]
        guidance.append(
            {
                "menu_id": meal_menu_item.menu_id,
                "menu_name": meal_menu_item.menu.name,
                "matched_allergens": matched,
                "is_restricted": bool(matched_codes),
                "recommendation_level": rec.recommendation_level.value,
                "recommended_serving_g": rec.recommended_serving_g,
            }
        )
    return CommonResponse(message="RFID 스캔이 완료되었습니다.", data=to_device_scan_response(card, meal, guidance))


@router.post("/meal-records", response_model=CommonResponse[MealRecordDetailResponse], status_code=status.HTTP_201_CREATED)
def create_meal_record(
    request: DeviceMealRecordCreateRequest,
    service: MealRecordService = Depends(get_meal_record_service),
):
    record = service.create_from_rfid(rfid_uid=request.rfid_uid, meal_id=request.meal_id)
    return CommonResponse(message="식사 기록이 생성되었습니다.", data=to_meal_record_response(record, NutritionService()))
