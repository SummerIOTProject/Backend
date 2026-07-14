from app.schemas.admin import AdminDashboardResponse, LeftoverSummaryItemResponse
from app.schemas.meal import MealDetailResponse, MealMenuItemResponse, NutritionPer100gSchema
from app.schemas.meal_analysis import MealAnalysisResponse
from app.schemas.meal_image import MealImageResponse
from app.schemas.meal_record import MealItemRecordResponse, MealRecordDetailResponse
from app.schemas.recommendation import RecommendationItemResponse
from app.schemas.rfid import DeviceMealResponse, DeviceMenuGuidanceResponse, DeviceRfidScanResponse, DeviceUserResponse


def to_meal_response(meal) -> MealDetailResponse:
    return MealDetailResponse(
        id=meal.id,
        meal_date=meal.meal_date,
        meal_type=meal.meal_type,
        school_name=meal.school_name,
        created_at=meal.created_at,
        updated_at=meal.updated_at,
        menu_items=[
            MealMenuItemResponse(
                meal_menu_item_id=item.id,
                menu_id=item.menu_id,
                name=item.menu.name,
                standard_serving_g=item.menu.standard_serving_g,
                nutrition_per_100g=NutritionPer100gSchema(
                    calories_kcal=item.menu.calories_per_100g,
                    carbohydrate_g=item.menu.carbohydrate_per_100g,
                    protein_g=item.menu.protein_per_100g,
                    fat_g=item.menu.fat_per_100g,
                ),
                ingredients=[link.ingredient.name for link in item.menu.ingredients],
                allergens=[link.allergen.code for link in item.menu.allergens],
            )
            for item in meal.meal_menu_items
        ],
    )


def to_meal_image_response(image) -> MealImageResponse:
    return MealImageResponse(
        id=image.id,
        meal_record_id=image.meal_record_id,
        image_type=image.image_type,
        image_url=f"/api/v1/me/meal-images/{image.id}",
        mime_type=image.mime_type,
        file_size=image.file_size,
        created_at=image.created_at,
    )


def to_meal_item_record_response(item, nutrition_service) -> MealItemRecordResponse:
    return MealItemRecordResponse(
        id=item.id,
        meal_record_id=item.meal_record_id,
        meal_menu_item_id=item.meal_menu_item_id,
        menu_id=item.meal_menu_item.menu_id,
        menu_name=item.meal_menu_item.menu.name,
        consumed_ratio=item.consumed_ratio,
        consumed_percent=round(item.consumed_ratio * 100, 2),
        consumption_level=item.consumption_level,
        confidence=item.confidence,
        is_corrected=item.is_corrected,
        corrected_at=item.corrected_at,
        corrected_by=item.corrected_by,
        note=item.note,
        analysis_type=item.analysis_type.value if hasattr(item.analysis_type, "value") else str(item.analysis_type),
        nutrition=nutrition_service.calculate(item.meal_menu_item.menu, item.consumed_ratio),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def to_meal_record_response(record, nutrition_service) -> MealRecordDetailResponse:
    return MealRecordDetailResponse(
        id=record.id,
        user_id=record.user_id,
        meal_id=record.meal_id,
        status=record.status,
        started_at=record.started_at,
        completed_at=record.completed_at,
        failure_reason=record.failure_reason,
        created_at=record.created_at,
        updated_at=record.updated_at,
        meal=to_meal_response(record.meal),
        images=[to_meal_image_response(image) for image in record.images],
        item_records=[to_meal_item_record_response(item, nutrition_service) for item in record.item_records],
    )


def to_recommendation_response(item) -> RecommendationItemResponse:
    return RecommendationItemResponse(
        meal_id=item.meal_id,
        meal_menu_item_id=item.meal_menu_item_id,
        menu_id=item.meal_menu_item.menu_id,
        menu_name=item.meal_menu_item.menu.name,
        standard_serving_g=item.meal_menu_item.menu.standard_serving_g,
        recommendation_level=item.recommendation_level,
        recommended_serving_ratio=item.recommended_serving_ratio,
        recommended_serving_g=item.recommended_serving_g,
        recent_average_consumed_ratio=item.recent_average_consumed_ratio,
        sample_count=item.sample_count,
        reason=item.reason,
    )


def to_device_scan_response(card, meal, guidance_items) -> DeviceRfidScanResponse:
    return DeviceRfidScanResponse(
        user=DeviceUserResponse(
            user_id=card.user.id,
            login_id=card.user.login_id,
            name=card.user.name,
            student_number=card.user.student_number,
        ),
        meal=DeviceMealResponse(**to_meal_response(meal).model_dump()),
        menu_guidance=guidance_items,
    )


def to_admin_dashboard_response(data: dict) -> AdminDashboardResponse:
    return AdminDashboardResponse(**data)


def to_leftover_summary_items(items: list[dict]) -> list[LeftoverSummaryItemResponse]:
    return [LeftoverSummaryItemResponse(**item) for item in items]
