from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_recommendation_service
from app.core.security import require_admin
from app.schemas.common import CommonResponse
from app.schemas.recommendation import ServingRecommendationItemResponse, ServingRecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/users/{user_id}/serving-recommendations", tags=["Recommendations"])


@router.get(
    "",
    summary="현재 식단 맞춤 배식 추천",
    description="현재 식단의 메뉴별 배식 추천을 생성합니다.",
    response_model=CommonResponse[ServingRecommendationResponse],
    status_code=status.HTTP_200_OK,
)
def get_serving_recommendations(
    user_id: int,
    meal_id: int = Query(...),
    service: RecommendationService = Depends(get_recommendation_service),
    _: object = Depends(require_admin),
):
    recommendations = service.generate_recommendations(user_id=user_id, meal_id=meal_id)
    data = ServingRecommendationResponse(
        user_id=user_id,
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
            for item in recommendations
        ],
    )
    return CommonResponse(success=True, message="맞춤 배식 추천 결과입니다.", data=data)


@router.get(
    "/history",
    summary="배식 추천 이력 조회",
    description="사용자의 배식 추천 이력을 조회합니다.",
    response_model=CommonResponse[ServingRecommendationResponse],
    status_code=status.HTTP_200_OK,
)
def get_recommendation_history(
    user_id: int,
    service: RecommendationService = Depends(get_recommendation_service),
    _: object = Depends(require_admin),
):
    items = service.list_history(user_id)
    data = ServingRecommendationResponse(
        user_id=user_id,
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
    return CommonResponse(success=True, message="배식 추천 이력입니다.", data=data)
