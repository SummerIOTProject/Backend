from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.repositories.rfid_repository import RfidRepository
from app.repositories.user_repository import UserRepository


class RfidService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rfid_repository = RfidRepository(db)
        self.user_repository = UserRepository(db)

    def register_my_card(self, user_id: int, uid: str):
        if self.rfid_repository.get_by_uid(uid):
            raise ConflictException(message="이미 등록된 RFID UID입니다.", code="RFID_ALREADY_REGISTERED", detail=uid)
        card = self.rfid_repository.create(user_id=user_id, uid=uid)
        self.db.commit()
        self.db.refresh(card)
        return card

    def get_active_card_by_uid(self, uid: str):
        card = self.rfid_repository.get_active_by_uid(uid)
        if not card:
            raise NotFoundException(message="RFID 카드를 찾을 수 없습니다.", code="RFID_NOT_FOUND", detail=uid)
        return card

    def list_my_cards(self, user_id: int):
        return self.rfid_repository.list_by_user(user_id)

    def deactivate_my_card(self, user_id: int, card_id: int):
        card = self.rfid_repository.get_by_id(card_id)
        if not card:
            raise NotFoundException(message="RFID 카드를 찾을 수 없습니다.", code="RFID_NOT_FOUND", detail=f"card_id={card_id}")
        if card.user_id != user_id:
            raise ForbiddenException(message="접근 권한이 없습니다.", code="FORBIDDEN_RESOURCE", detail=f"card_id={card_id}")
        card.is_active = False
        self.db.commit()
        self.db.refresh(card)
        return card
