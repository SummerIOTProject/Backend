import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.database import get_db
from app.repositories.user_repository import UserRepository


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 100_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = hashed_password.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    iterations = int(iterations_raw)
    salt = _b64url_decode(salt_raw)
    expected_digest = _b64url_decode(digest_raw)
    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(expires_at.timestamp()),
    }
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, object]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise UnauthorizedException(
            message="유효하지 않은 토큰입니다.",
            code="INVALID_TOKEN",
            detail="토큰 형식이 올바르지 않습니다.",
        ) from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected_signature), encoded_signature):
        raise UnauthorizedException(
            message="유효하지 않은 토큰입니다.",
            code="INVALID_TOKEN",
            detail="토큰 서명이 일치하지 않습니다.",
        )

    try:
        payload = json.loads(_b64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise UnauthorizedException(
            message="유효하지 않은 토큰입니다.",
            code="INVALID_TOKEN",
            detail="토큰 payload를 해석할 수 없습니다.",
        ) from exc

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= int(datetime.now(UTC).timestamp()):
        raise UnauthorizedException(
            message="토큰이 만료되었습니다.",
            code="TOKEN_EXPIRED",
            detail="다시 로그인해 주세요.",
        )
    return payload


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedException(
            message="인증이 필요합니다.",
            code="AUTH_REQUIRED",
            detail="Authorization 헤더가 필요합니다.",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(
            message="인증이 필요합니다.",
            code="INVALID_AUTH_HEADER",
            detail="Bearer 토큰 형식이 필요합니다.",
        )
    return token


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    token = _extract_bearer_token(authorization)
    payload = decode_access_token(token)
    user_id_raw = payload.get("sub")
    if not isinstance(user_id_raw, str) or not user_id_raw.isdigit():
        raise UnauthorizedException(
            message="유효하지 않은 토큰입니다.",
            code="INVALID_TOKEN",
            detail="토큰 사용자 정보가 올바르지 않습니다.",
        )
    user = UserRepository(db).get_by_id(int(user_id_raw))
    if not user:
        raise UnauthorizedException(
            message="사용자를 찾을 수 없습니다.",
            code="USER_NOT_FOUND",
            detail=f"user_id={user_id_raw}",
        )
    return user


def require_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise UnauthorizedException(
            message="비활성화된 계정입니다.",
            code="INACTIVE_USER",
            detail=f"user_id={current_user.id}",
        )
    return current_user


def require_admin(current_user=Depends(require_active_user)):
    if current_user.role != "ADMIN":
        raise UnauthorizedException(
            message="관리자 권한이 필요합니다.",
            code="ADMIN_REQUIRED",
            detail=f"user_id={current_user.id}",
        )
    return current_user


def verify_admin_api_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> str:
    expected = settings.ADMIN_API_KEY
    if not expected or x_admin_key != expected:
        raise UnauthorizedException(
            message="관리자 인증에 실패했습니다.",
            code="UNAUTHORIZED",
            detail="유효한 X-Admin-Key 헤더가 필요합니다.",
        )
    return x_admin_key
