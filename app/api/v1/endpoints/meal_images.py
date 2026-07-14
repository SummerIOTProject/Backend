from io import BytesIO

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.dependencies import get_image_service, get_meal_record_service
from app.api.mappers.response_mappers import to_meal_image_response
from app.core.security import get_current_user
from app.schemas.common import CommonResponse
from app.schemas.meal_image import MealImageResponse, MealImageUploadResponse
from app.services.image_service import ImageService
from app.services.meal_record_service import MealRecordService
from app.utils.enums import ImageType

router = APIRouter(tags=["Meal Images"])


@router.post("/me/meal-records/{meal_record_id}/images/before", response_model=CommonResponse[MealImageUploadResponse], status_code=status.HTTP_201_CREATED)
def upload_my_before_image(
    meal_record_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service),
    record_service: MealRecordService = Depends(get_meal_record_service),
):
    record_service.assert_owner(meal_record_id, current_user.id)
    image = image_service.upload_image(meal_record_id, ImageType.BEFORE, file)
    return CommonResponse(message="식전 이미지가 업로드되었습니다.", data=MealImageUploadResponse(image_id=image.id, image_url=f"/api/v1/me/meal-images/{image.id}"))


@router.post("/me/meal-records/{meal_record_id}/images/after", response_model=CommonResponse[MealImageUploadResponse], status_code=status.HTTP_201_CREATED)
def upload_my_after_image(
    meal_record_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service),
    record_service: MealRecordService = Depends(get_meal_record_service),
):
    record_service.assert_owner(meal_record_id, current_user.id)
    image = image_service.upload_image(meal_record_id, ImageType.AFTER, file)
    return CommonResponse(message="식후 이미지가 업로드되었습니다.", data=MealImageUploadResponse(image_id=image.id, image_url=f"/api/v1/me/meal-images/{image.id}"))


@router.get("/me/meal-records/{meal_record_id}/images", response_model=CommonResponse[list[MealImageResponse]])
def list_my_images(
    meal_record_id: int,
    current_user=Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service),
    record_service: MealRecordService = Depends(get_meal_record_service),
):
    record_service.assert_owner(meal_record_id, current_user.id)
    images = image_service.list_images(meal_record_id)
    return CommonResponse(message="이미지 목록입니다.", data=[to_meal_image_response(image) for image in images])


@router.get("/me/meal-images/{image_id}")
def get_my_meal_image(image_id: int, current_user=Depends(get_current_user), image_service: ImageService = Depends(get_image_service)):
    image = image_service.get_image_for_user(image_id, current_user.id, is_admin=(getattr(current_user.role, "value", current_user.role) == "ADMIN"))
    headers = {"X-Content-Type-Options": "nosniff"}
    path = image_service.resolve_image_path(image)
    if path is not None:
        return FileResponse(path=path, media_type=image.mime_type, headers=headers)
    return StreamingResponse(BytesIO(image_service.read_image_bytes(image)), media_type=image.mime_type, headers=headers)
