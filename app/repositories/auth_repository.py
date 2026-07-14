from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_refresh_token(self, *, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(token)
        self.db.flush()
        return token

    def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalar(stmt)

    def revoke_refresh_token(self, refresh_token: RefreshToken, revoked_at: datetime) -> RefreshToken:
        refresh_token.revoked_at = revoked_at
        self.db.flush()
        return refresh_token

    def revoke_all_by_user_id(self, user_id: int, revoked_at: datetime) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
