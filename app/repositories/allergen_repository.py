from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.allergen import Allergen
from app.models.user_allergy import UserAllergy


class AllergenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self) -> list[Allergen]:
        stmt = select(Allergen).where(Allergen.is_active.is_(True)).order_by(Allergen.display_number.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_codes(self, codes: list[str]) -> list[Allergen]:
        if not codes:
            return []
        stmt = select(Allergen).where(Allergen.code.in_(codes), Allergen.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def replace_user_allergies(self, user_id: int, allergen_ids: list[int]) -> None:
        self.db.query(UserAllergy).filter(UserAllergy.user_id == user_id).delete()
        for allergen_id in allergen_ids:
            self.db.add(UserAllergy(user_id=user_id, allergen_id=allergen_id))
        self.db.flush()
