from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.rfid_repository import RfidRepository
from app.repositories.user_repository import UserRepository
from app.schemas.rfid import RfidCardCreateRequest, RfidScanRequest


class RfidService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rfid_repository = RfidRepository(db)
        self.user_repository = UserRepository(db)

    def register_card(self, request: RfidCardCreateRequest):
        user = self.user_repository.get_by_id(request.user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={request.user_id}에 해당하는 사용자가 없습니다.",
            )
        existing = self.rfid_repository.get_by_uid(request.uid)
        if existing:
            raise ConflictException(
                message="이미 등록된 RFID UID입니다.",
                code="DUPLICATE_RFID_UID",
                detail=f"uid={request.uid}",
            )
        card = self.rfid_repository.create(user_id=request.user_id, uid=request.uid)
        self.db.commit()
        self.db.refresh(card)
        return card

    def scan_card(self, request: RfidScanRequest):
        card = self.rfid_repository.get_active_by_uid(request.uid)
        if not card:
            raise NotFoundException(
                message="활성 RFID 카드를 찾을 수 없습니다.",
                code="RFID_NOT_FOUND",
                detail=f"uid={request.uid}",
            )
        return card

    def deactivate_card(self, card_id: int):
        card = self.rfid_repository.get_by_id(card_id)
        if not card:
            raise NotFoundException(
                message="RFID 카드를 찾을 수 없습니다.",
                code="RFID_NOT_FOUND",
                detail=f"card_id={card_id}",
            )
        card = self.rfid_repository.deactivate(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def list_user_cards(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}에 해당하는 사용자가 없습니다.",
            )
        return self.rfid_repository.list_by_user(user_id)
