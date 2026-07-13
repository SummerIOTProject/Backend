from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.repositories.meal_image_repository import MealImageRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.utils.enums import ImageType
from app.utils.files import (
    build_storage_path,
    delete_file_if_exists,
    generate_filename_for_extension,
    read_upload_file,
    resolve_storage_path,
    save_image_bytes,
)


class ImageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.image_repository = MealImageRepository(db)
        self.meal_record_repository = MealRecordRepository(db)

    def upload_image(self, meal_record_id: int, image_type: ImageType, file: UploadFile):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise NotFoundException(message="식사 기록을 찾을 수 없습니다.", code="MEAL_RECORD_NOT_FOUND", detail=f"meal_record_id={meal_record_id}")
        if image_type == ImageType.AFTER and not self.image_repository.get_by_record_and_type(meal_record_id, ImageType.BEFORE):
            raise BadRequestException(message="식전 이미지가 먼저 필요합니다.", code="BEFORE_IMAGE_REQUIRED", detail="before image missing")
        file_bytes, mime_type, extension = read_upload_file(file)
        existing = self.image_repository.get_by_record_and_type(meal_record_id, image_type)
        old_path = None
        if existing:
            old_path = resolve_storage_path(existing.image_url)
        generated_name = generate_filename_for_extension(extension)
        saved_path = ""
        try:
            generated_name, saved_path = save_image_bytes(file_bytes=file_bytes, filename=generated_name, image_type=image_type.value)
            image = self.image_repository.create_or_replace(
                existing,
                meal_record_id=meal_record_id,
                image_type=image_type,
                image_url=build_storage_path(image_type.value, generated_name),
                mime_type=mime_type,
                file_size=len(file_bytes),
            )
            self.db.commit()
            if old_path:
                delete_file_if_exists(old_path)
            self.db.refresh(image)
            return image
        except Exception:
            self.db.rollback()
            delete_file_if_exists(saved_path)
            raise

    def list_images(self, meal_record_id: int):
        return self.image_repository.list_by_record(meal_record_id)

    def get_image_for_user(self, image_id: int, user_id: int, is_admin: bool = False):
        image = self.image_repository.get_by_id(image_id)
        if not image:
            raise NotFoundException(message="이미지를 찾을 수 없습니다.", code="IMAGE_NOT_FOUND", detail=f"image_id={image_id}")
        if not is_admin and image.meal_record.user_id != user_id:
            raise ForbiddenException(message="접근 권한이 없습니다.", code="FORBIDDEN_RESOURCE", detail=f"image_id={image_id}")
        return image

    def resolve_image_path(self, image) -> Path:
        return resolve_storage_path(image.image_url)
