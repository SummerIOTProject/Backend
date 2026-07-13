from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.repositories.user_repository import UserRepository
from app.utils.enums import UserRole

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _jwt_encode(payload: dict[str, object]) -> str:
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    encoded_header = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64_encode(signature)}"


def _jwt_decode(token: str) -> dict[str, object]:
    try:
        header, payload, signature = token.split(".")
    except ValueError as exc:
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="토큰 형식 오류") from exc

    signing_input = f"{header}.{payload}".encode("ascii")
    expected = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64_encode(expected), signature):
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="토큰 서명 불일치")
    try:
        data = json.loads(_b64_decode(payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="토큰 해석 실패") from exc
    exp = data.get("exp")
    if not isinstance(exp, int):
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="만료 시각 누락")
    if exp <= int(datetime.now(UTC).timestamp()):
        raise UnauthorizedException(message="토큰이 만료되었습니다.", code="TOKEN_EXPIRED", detail="다시 로그인해 주세요.")
    return data


def create_access_token(user_id: int, role: UserRole | str) -> str:
    now = datetime.now(UTC)
    role_value = role.value if isinstance(role, UserRole) else str(role)
    payload = {
        "sub": str(user_id),
        "role": role_value,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return _jwt_encode(payload)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": secrets.token_urlsafe(24),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _jwt_encode(payload), expires_at


def decode_token(token: str) -> dict[str, object]:
    return _jwt_decode(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_password_format(password: str) -> None:
    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(not char.isalnum() for char in password)
    if len(password) < 8 or not (has_upper and has_lower and has_digit and has_special):
        raise UnauthorizedException(
            message="비밀번호 형식이 올바르지 않습니다.",
            code="INVALID_PASSWORD_FORMAT",
            detail="비밀번호는 8자 이상이며 대문자, 소문자, 숫자, 특수문자를 포함해야 합니다.",
        )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedException(message="인증이 필요합니다.", code="INVALID_TOKEN", detail="Authorization 헤더가 필요합니다.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="Bearer 토큰 형식 필요")
    return token


def get_current_user(authorization: str | None = Header(default=None, alias="Authorization"), db: Session = Depends(get_db)):
    token = _extract_bearer_token(authorization)
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="Access token만 허용됩니다.")
    raw_user_id = payload.get("sub")
    if not isinstance(raw_user_id, str) or not raw_user_id.isdigit():
        raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="사용자 정보가 올바르지 않습니다.")
    user = UserRepository(db).get_by_id(int(raw_user_id))
    if not user:
        raise UnauthorizedException(message="사용자를 찾을 수 없습니다.", code="USER_NOT_FOUND", detail=f"user_id={raw_user_id}")
    if not user.is_active:
        raise UnauthorizedException(message="비활성화된 계정입니다.", code="INACTIVE_USER", detail=f"user_id={user.id}")
    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException(message="관리자 권한이 필요합니다.", code="ADMIN_REQUIRED", detail=f"user_id={current_user.id}")
    return current_user


def require_device_key(x_device_key: str | None = Header(default=None, alias="X-Device-Key")) -> str:
    if not x_device_key or x_device_key != settings.DEVICE_API_KEY:
        raise UnauthorizedException(message="장치 인증에 실패했습니다.", code="INVALID_DEVICE_KEY", detail="유효한 X-Device-Key 필요")
    return x_device_key
