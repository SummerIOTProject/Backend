from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal_image import MealImage
from app.utils.enums import ImageType


class ImageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_record_and_type(self, meal_record_id: int, image_type: ImageType) -> MealImage | None:
        stmt = select(MealImage).where(
            MealImage.meal_record_id == meal_record_id,
            MealImage.image_type == image_type,
        )
        return self.db.scalar(stmt)

    def create_or_replace(
        self,
        *,
        existing: MealImage | None,
        meal_record_id: int,
        image_type: ImageType,
        image_url: str,
        original_filename: str | None,
        content_type: str | None,
    ) -> MealImage:
        if existing:
            existing.image_url = image_url
            existing.original_filename = original_filename
            existing.content_type = content_type
            self.db.flush()
            return existing

        image = MealImage(
            meal_record_id=meal_record_id,
            image_type=image_type,
            image_url=image_url,
            original_filename=original_filename,
            content_type=content_type,
        )
        self.db.add(image)
        self.db.flush()
        return image

    def list_by_record(self, meal_record_id: int) -> list[MealImage]:
        stmt = select(MealImage).where(MealImage.meal_record_id == meal_record_id).order_by(MealImage.id.asc())
        return list(self.db.scalars(stmt).all())

    def delete(self, image: MealImage) -> None:
        self.db.delete(image)
        self.db.flush()
