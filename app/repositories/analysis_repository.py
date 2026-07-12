from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.meal_analysis import MealAnalysis


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_or_update(
        self,
        *,
        existing: MealAnalysis | None,
        meal_record_id: int,
        meal_menu_item_id: int,
        consumed_ratio: float,
        consumption_level,
        confidence: float | None,
        note: str | None,
    ) -> MealAnalysis:
        if existing:
            existing.consumed_ratio = consumed_ratio
            existing.consumption_level = consumption_level
            existing.confidence = confidence
            existing.note = note
            self.db.flush()
            return existing

        analysis = MealAnalysis(
            meal_record_id=meal_record_id,
            meal_menu_item_id=meal_menu_item_id,
            consumed_ratio=consumed_ratio,
            consumption_level=consumption_level,
            confidence=confidence,
            note=note,
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def list_by_record(self, meal_record_id: int) -> list[MealAnalysis]:
        stmt = (
            select(MealAnalysis)
            .options(joinedload(MealAnalysis.meal_menu_item))
            .where(MealAnalysis.meal_record_id == meal_record_id)
            .order_by(MealAnalysis.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_record_and_menu_item(self, meal_record_id: int, meal_menu_item_id: int) -> MealAnalysis | None:
        stmt = select(MealAnalysis).where(
            MealAnalysis.meal_record_id == meal_record_id,
            MealAnalysis.meal_menu_item_id == meal_menu_item_id,
        )
        return self.db.scalar(stmt)

    def delete_by_record(self, meal_record_id: int) -> None:
        self.db.execute(delete(MealAnalysis).where(MealAnalysis.meal_record_id == meal_record_id))
        self.db.flush()
