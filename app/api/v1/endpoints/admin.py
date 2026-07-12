from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_recommendation_service
from app.core.security import verify_admin_api_key
from app.schemas.common import AdminDashboardResponse, CommonResponse, LeftoverSummaryResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(verify_admin_api_key)])


@router.get(
    "/dashboard",
    summary="관리자 대시보드 통계",
    description="특정 날짜 기준 사용자, 기록, 분석 통계를 조회합니다.",
    response_model=CommonResponse[AdminDashboardResponse],
    status_code=status.HTTP_200_OK,
)
def get_dashboard(
    date_value: date = Query(..., alias="date"),
    service: RecommendationService = Depends(get_recommendation_service),
):
    result = service.get_admin_dashboard(date_value)
    return CommonResponse(success=True, message="관리자 대시보드 통계입니다.", data=AdminDashboardResponse.model_validate(result))


@router.get(
    "/leftover-summary",
    summary="잔반 요약 통계",
    description="기간 내 메뉴별 평균 섭취율과 잔반율을 조회합니다.",
    response_model=CommonResponse[LeftoverSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_leftover_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: RecommendationService = Depends(get_recommendation_service),
):
    result = service.get_leftover_summary(start_date=start_date, end_date=end_date)
    return CommonResponse(success=True, message="잔반 요약 통계입니다.", data=LeftoverSummaryResponse.model_validate(result))
