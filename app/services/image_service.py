import logging

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.repositories.meal_image_repository import MealImageRepository
from app.repositories.meal_record_repository import MealRecordRepository
from app.services.meal_record_service import MealRecordService
from app.services.storage.factory import build_image_storage
from app.utils.enums import ImageType
from app.utils.files import (
    generate_filename_for_extension,
    read_upload_file,
)

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.image_repository = MealImageRepository(db)
        self.meal_record_repository = MealRecordRepository(db)
        self.meal_record_service = MealRecordService(db)
        self.storage = build_image_storage()

    def upload_image(self, meal_record_id: int, image_type: ImageType, file: UploadFile):
        record = self.meal_record_repository.get_by_id(meal_record_id)
        if not record:
            raise NotFoundException(message="식사 기록을 찾을 수 없습니다.", code="MEAL_RECORD_NOT_FOUND", detail=f"meal_record_id={meal_record_id}")
        file_bytes, mime_type, extension = read_upload_file(file)
        existing = self.image_repository.get_by_record_and_type(meal_record_id, image_type)
        old_key = existing.image_url if existing else None
        generated_name = generate_filename_for_extension(extension)
        storage_key = self.storage.build_key(meal_record_id=meal_record_id, image_type=image_type, filename=generated_name)
        saved_key = ""
        try:
            saved_key = self.storage.save(key=storage_key, content=file_bytes, content_type=mime_type)
            image = self.image_repository.create_or_replace(
                existing,
                meal_record_id=meal_record_id,
                image_type=image_type,
                image_url=saved_key,
                mime_type=mime_type,
                file_size=len(file_bytes),
            )
            self.meal_record_service.recalculate_status_after_image_change(meal_record_id)
            self.db.commit()
            if old_key and old_key != saved_key:
                self._delete_storage_key_quietly(old_key, meal_record_id=meal_record_id, image_type=image_type)
            self.db.refresh(image)
            return image
        except Exception:
            self.db.rollback()
            if saved_key:
                self._delete_storage_key_quietly(saved_key, meal_record_id=meal_record_id, image_type=image_type)
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

    def resolve_image_path(self, image):
        path = self.storage.resolve_local_path(image.image_url)
        if path is not None and not path.exists():
            raise NotFoundException(message="이미지 파일을 찾을 수 없습니다.", code="IMAGE_FILE_NOT_FOUND", detail=f"image_id={image.id}")
        return path

    def read_image_bytes(self, image) -> bytes:
        return self.storage.read(image.image_url)

    def _delete_storage_key_quietly(self, key: str, *, meal_record_id: int, image_type: ImageType) -> None:
        try:
            self.storage.delete(key)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", type(exc).__name__)
            logger.warning(
                "failed_to_delete_image_storage_object backend=%s operation=delete meal_record_id=%s image_type=%s error_code=%s",
                getattr(self.storage, "backend_name", "UNKNOWN"),
                meal_record_id,
                image_type.value,
                code,
            )
            return
