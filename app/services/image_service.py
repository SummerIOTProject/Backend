from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.image_repository import ImageRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.utils.enums import ImageType, MealRecordStatus
from app.utils.file import (
    build_upload_url,
    delete_file_if_exists,
    ensure_directory,
    save_bytes_file,
    validate_extension,
    validate_file_size,
    validate_mime_type,
)


class ImageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.image_repository = ImageRepository(db)
        self.meal_record_repository = MealRecordRepository(db)

    def _record_or_raise(self, meal_record_id: int):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise NotFoundException(
                message="식사 기록을 찾을 수 없습니다.",
                code="MEAL_RECORD_NOT_FOUND",
                detail=f"meal_record_id={meal_record_id}",
            )
        return record

    def _save_image(self, meal_record_id: int, image_type: ImageType, file: UploadFile):
        record = self._record_or_raise(meal_record_id)
        if image_type == ImageType.AFTER:
            before_image = self.image_repository.get_by_record_and_type(meal_record_id, ImageType.BEFORE)
            if not before_image:
                raise BadRequestException(
                    message="식전 이미지가 먼저 필요합니다.",
                    code="BEFORE_IMAGE_REQUIRED",
                    detail="식전 사진 업로드 후 식후 사진을 업로드하세요.",
                )
        validate_mime_type(file.content_type)
        validate_extension(file.filename or "upload.jpg")
        file_bytes = file.file.read()
        validate_file_size(file_bytes)
        file.file.seek(0)
        subdir = image_type.value.lower()
        destination_dir = Path(settings.UPLOAD_DIR) / subdir
        ensure_directory(destination_dir)
        existing = self.image_repository.get_by_record_and_type(meal_record_id, image_type)
        if existing:
            delete_file_if_exists(Path(settings.UPLOAD_DIR) / existing.image_url.replace("/uploads/", ""))
        filename, _ = save_bytes_file(file_bytes, file.filename or "upload.jpg", destination_dir)
        image_url = build_upload_url(subdir, filename)
        image = self.image_repository.create_or_replace(
            existing=existing,
            meal_record_id=meal_record_id,
            image_type=image_type,
            image_url=image_url,
            original_filename=file.filename,
            content_type=file.content_type,
        )

        if image_type == ImageType.BEFORE:
            status = MealRecordStatus.BEFORE_IMAGE_UPLOADED
        else:
            status = MealRecordStatus.IMAGES_UPLOADED
        self.meal_record_repository.update_status(record, status=status, completed_at=None, failure_reason=None)
        self.db.commit()
        self.db.refresh(image)
        return image

    def upload_before_image(self, meal_record_id: int, file: UploadFile):
        return self._save_image(meal_record_id, ImageType.BEFORE, file)

    def upload_after_image(self, meal_record_id: int, file: UploadFile):
        return self._save_image(meal_record_id, ImageType.AFTER, file)

    def list_images(self, meal_record_id: int):
        self._record_or_raise(meal_record_id)
        return self.image_repository.list_by_record(meal_record_id)

    def delete_image(self, meal_record_id: int, image_type: ImageType) -> None:
        record = self._record_or_raise(meal_record_id)
        image = self.image_repository.get_by_record_and_type(meal_record_id, image_type)
        if not image:
            raise BadRequestException(
                message="이미지를 찾을 수 없습니다.",
                code="INVALID_IMAGE_TYPE",
                detail=f"image_type={image_type}",
            )
        delete_file_if_exists(Path(settings.UPLOAD_DIR) / image.image_url.replace("/uploads/", ""))
        self.image_repository.delete(image)
        remaining = self.image_repository.list_by_record(meal_record_id)
        if any(item.image_type == ImageType.AFTER for item in remaining):
            status = MealRecordStatus.IMAGES_UPLOADED
        elif any(item.image_type == ImageType.BEFORE for item in remaining):
            status = MealRecordStatus.BEFORE_IMAGE_UPLOADED
        else:
            status = MealRecordStatus.CREATED
        self.meal_record_repository.update_status(record, status=status, completed_at=None, failure_reason=None)
        self.db.commit()
