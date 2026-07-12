from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.rfid_card import RFIDCard


class RfidRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: int, uid: str) -> RFIDCard:
        card = RFIDCard(user_id=user_id, uid=uid, is_active=True)
        self.db.add(card)
        self.db.flush()
        return card

    def get_by_uid(self, uid: str) -> RFIDCard | None:
        stmt = select(RFIDCard).options(joinedload(RFIDCard.user)).where(RFIDCard.uid == uid)
        return self.db.scalar(stmt)

    def get_active_by_uid(self, uid: str) -> RFIDCard | None:
        stmt = (
            select(RFIDCard)
            .options(joinedload(RFIDCard.user))
            .where(RFIDCard.uid == uid, RFIDCard.is_active.is_(True))
        )
        return self.db.scalar(stmt)

    def get_by_id(self, card_id: int) -> RFIDCard | None:
        stmt = select(RFIDCard).options(joinedload(RFIDCard.user)).where(RFIDCard.id == card_id)
        return self.db.scalar(stmt)

    def list_by_user(self, user_id: int) -> list[RFIDCard]:
        stmt = (
            select(RFIDCard)
            .options(joinedload(RFIDCard.user))
            .where(RFIDCard.user_id == user_id)
            .order_by(RFIDCard.registered_at.desc(), RFIDCard.id.desc())
        )
        return list(self.db.scalars(stmt).all())

    def deactivate(self, card: RFIDCard) -> RFIDCard:
        card.is_active = False
        self.db.flush()
        return card
