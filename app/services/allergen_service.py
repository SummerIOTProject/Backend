from app.core.exceptions import BadRequestException
from sqlalchemy.orm import Session

from app.repositories.allergen_repository import AllergenRepository
from app.repositories.user_repository import UserRepository
from app.utils.normalization import normalize_allergen_codes


class AllergenService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.allergen_repository = AllergenRepository(db)
        self.user_repository = UserRepository(db)

    def list_allergens(self):
        return self.allergen_repository.list_active()

    def get_my_allergies(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        return [item.allergen for item in user.allergies]

    def replace_my_allergies(self, user_id: int, codes: list[str]):
        normalized_codes = normalize_allergen_codes(codes)
        allergens = self.allergen_repository.get_by_codes(normalized_codes)
        if len(allergens) != len(normalized_codes):
            raise BadRequestException(message="유효하지 않은 알레르기 코드가 있습니다.", code="INVALID_ALLERGEN_CODE", detail="unknown allergen code")
        self.allergen_repository.replace_user_allergies(user_id, [item.id for item in allergens])
        self.db.commit()
        return allergens
