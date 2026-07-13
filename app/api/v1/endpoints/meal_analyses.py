from fastapi import APIRouter, Depends

from app.api.mappers.response_mappers import to_meal_item_record_response
from app.api.dependencies import get_analysis_service, get_nutrition_service
from app.core.security import get_current_user
from app.schemas.common import CommonResponse
from app.schemas.meal_analysis import MealAnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.nutrition_service import NutritionService

router = APIRouter(tags=["Meal Analyses"])


@router.post("/me/meal-records/{meal_record_id}/analyze", response_model=CommonResponse[MealAnalysisResponse])
async def analyze_my_meal_record(
    meal_record_id: int,
    current_user=Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    item_records, analysis_type, analysis_note = await service.analyze(meal_record_id, user_id=current_user.id)
    return CommonResponse(
        message="식사 분석이 완료되었습니다.",
        data=MealAnalysisResponse(
            meal_record_id=meal_record_id,
            analysis_type=analysis_type,
            analysis_note=analysis_note,
            items=[to_meal_item_record_response(item, nutrition_service) for item in item_records],
        ),
    )


@router.post("/me/meal-records/{meal_record_id}/reanalyze", response_model=CommonResponse[MealAnalysisResponse])
async def reanalyze_my_meal_record(
    meal_record_id: int,
    current_user=Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    item_records, analysis_type, analysis_note = await service.reanalyze(meal_record_id, user_id=current_user.id)
    return CommonResponse(
        message="식사 재분석이 완료되었습니다.",
        data=MealAnalysisResponse(
            meal_record_id=meal_record_id,
            analysis_type=analysis_type,
            analysis_note=analysis_note,
            items=[to_meal_item_record_response(item, nutrition_service) for item in item_records],
        ),
    )
