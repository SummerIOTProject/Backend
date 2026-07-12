from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_image_service
from app.schemas.common import CommonResponse
from app.schemas.meal_image import MealImageListResponse, MealImageResponse
from app.services.image_service import ImageService
from app.utils.enums import ImageType

router = APIRouter(tags=["Meal Images"])


@router.post(
    "/meal-records/{meal_record_id}/images/before",
    summary="식전 이미지 업로드",
    description="식전 급식판 이미지를 업로드합니다.",
    response_model=CommonResponse[MealImageResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_before_image(
    meal_record_id: int,
    file: UploadFile = File(...),
    service: ImageService = Depends(get_image_service),
):
    image = service.upload_before_image(meal_record_id, file)
    return CommonResponse(success=True, message="식전 이미지가 업로드되었습니다.", data=MealImageResponse.model_validate(image))


@router.post(
    "/meal-records/{meal_record_id}/images/after",
    summary="식후 이미지 업로드",
    description="식후 급식판 이미지를 업로드합니다.",
    response_model=CommonResponse[MealImageResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_after_image(
    meal_record_id: int,
    file: UploadFile = File(...),
    service: ImageService = Depends(get_image_service),
):
    image = service.upload_after_image(meal_record_id, file)
    return CommonResponse(success=True, message="식후 이미지가 업로드되었습니다.", data=MealImageResponse.model_validate(image))


@router.get(
    "/meal-records/{meal_record_id}/images",
    summary="식사 기록 이미지 목록",
    description="식사 기록의 업로드된 이미지 목록을 조회합니다.",
    response_model=CommonResponse[MealImageListResponse],
    status_code=status.HTTP_200_OK,
)
def list_images(meal_record_id: int, service: ImageService = Depends(get_image_service)):
    images = service.list_images(meal_record_id)
    data = MealImageListResponse(items=[MealImageResponse.model_validate(item) for item in images], total=len(images))
    return CommonResponse(success=True, message="이미지 목록입니다.", data=data)


@router.delete(
    "/meal-records/{meal_record_id}/images/{image_type}",
    summary="식사 기록 이미지 삭제",
    description="식사 기록의 특정 이미지를 삭제합니다.",
    response_model=CommonResponse[None],
    status_code=status.HTTP_200_OK,
)
def delete_image(meal_record_id: int, image_type: ImageType, service: ImageService = Depends(get_image_service)):
    service.delete_image(meal_record_id, image_type)
    return CommonResponse(success=True, message="이미지가 삭제되었습니다.", data=None)
