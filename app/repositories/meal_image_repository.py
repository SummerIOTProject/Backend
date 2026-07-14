from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from app.models.meal_image import MealImage
from app.utils.enums import ImageType


class MealImageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_record_and_type(self, meal_record_id: int, image_type: ImageType) -> MealImage | None:
        stmt = select(MealImage).where(MealImage.meal_record_id == meal_record_id, MealImage.image_type == image_type)
        return self.db.scalar(stmt)

    def list_by_record(self, meal_record_id: int) -> list[MealImage]:
        stmt = select(MealImage).where(MealImage.meal_record_id == meal_record_id).order_by(MealImage.id.asc())
        return list(self.db.scalars(stmt).all())

    def has_image_type(self, meal_record_id: int, image_type: ImageType) -> bool:
        return self.get_by_record_and_type(meal_record_id, image_type) is not None

    def get_by_id(self, image_id: int) -> MealImage | None:
        stmt = select(MealImage).options(joinedload(MealImage.meal_record)).where(MealImage.id == image_id)
        return self.db.scalar(stmt)

    def create_or_replace(self, existing: MealImage | None, **kwargs) -> MealImage:
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        image = MealImage(**kwargs)
        self.db.add(image)
        self.db.flush()
        return image
