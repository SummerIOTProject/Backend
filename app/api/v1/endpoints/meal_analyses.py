from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_analysis_service
from app.schemas.common import CommonResponse
from app.schemas.meal_analysis import MealAnalyzeRequest, MealAnalysisResponse, MealReanalyzeRequest
from app.schemas.meal_record import MealRecordResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(tags=["Meal Analyses"])


@router.post(
    "/meal-records/{meal_record_id}/analyze",
    summary="식사 기록 분석 실행",
    description="식전/식후 이미지를 바탕으로 섭취 분석을 수행합니다.",
    response_model=CommonResponse[MealAnalysisResponse],
    status_code=status.HTTP_200_OK,
)
def analyze_meal_record(
    meal_record_id: int,
    request: MealAnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.analyze(meal_record_id, request)
    return CommonResponse(success=True, message="식사 분석이 완료되었습니다.", data=MealAnalysisResponse.model_validate(result))


@router.post(
    "/meal-records/{meal_record_id}/reanalyze",
    summary="식사 기록 재분석",
    description="기존 분석 결과를 삭제하고 다시 분석합니다.",
    response_model=CommonResponse[MealAnalysisResponse],
    status_code=status.HTTP_200_OK,
)
def reanalyze_meal_record(
    meal_record_id: int,
    request: MealReanalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.reanalyze(meal_record_id, request)
    return CommonResponse(success=True, message="식사 재분석이 완료되었습니다.", data=MealAnalysisResponse.model_validate(result))


@router.get(
    "/meal-records/{meal_record_id}/analysis",
    summary="식사 기록 분석 조회",
    description="저장된 식사 분석 결과를 조회합니다.",
    response_model=CommonResponse[MealAnalysisResponse],
    status_code=status.HTTP_200_OK,
)
def get_analysis(meal_record_id: int, service: AnalysisService = Depends(get_analysis_service)):
    result = service.get_analysis(meal_record_id)
    return CommonResponse(success=True, message="식사 분석 결과입니다.", data=MealAnalysisResponse.model_validate(result))
