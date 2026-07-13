from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.mappers.response_mappers import to_admin_dashboard_response, to_leftover_summary_items
from app.api.dependencies import get_recommendation_service, get_user_service
from app.core.security import require_admin
from app.schemas.admin import AdminDashboardResponse, AdminUserListResponse, LeftoverSummaryItemResponse
from app.schemas.common import CommonResponse
from app.schemas.user import UserResponse
from app.services.recommendation_service import RecommendationService
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=CommonResponse[AdminUserListResponse])
def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    service: UserService = Depends(get_user_service),
):
    items, total = service.list_users(page=page, size=size, keyword=keyword, is_active=is_active)
    return CommonResponse(
        message="사용자 목록입니다.",
        data=AdminUserListResponse(items=[UserResponse.model_validate(item) for item in items], page=page, size=size, total=total),
    )


@router.get("/dashboard", response_model=CommonResponse[AdminDashboardResponse])
def get_dashboard(date_value: date = Query(..., alias="date"), service: RecommendationService = Depends(get_recommendation_service)):
    return CommonResponse(message="관리자 대시보드입니다.", data=to_admin_dashboard_response(service.get_dashboard(date_value)))


@router.get("/leftover-summary", response_model=CommonResponse[list[LeftoverSummaryItemResponse]])
def get_leftover_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return CommonResponse(message="잔반 통계입니다.", data=to_leftover_summary_items(service.get_leftover_summary(start_date, end_date)))
