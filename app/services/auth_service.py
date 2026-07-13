from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_format,
    verify_password,
)
from app.repositories.allergen_repository import AllergenRepository
from app.repositories.auth_repository import AuthRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SignUpRequest,
    TokenPairResponse,
)
from app.utils.enums import UserRole


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.auth_repository = AuthRepository(db)
        self.allergen_repository = AllergenRepository(db)

    def signup(self, request: SignUpRequest):
        if self.user_repository.get_by_login_id(request.login_id):
            raise ConflictException(message="이미 사용 중인 로그인 ID입니다.", code="DUPLICATE_LOGIN_ID", detail=request.login_id)
        if self.user_repository.get_by_student_number(request.student_number):
            raise ConflictException(
                message="이미 사용 중인 학번입니다.",
                code="DUPLICATE_STUDENT_NUMBER",
                detail=request.student_number,
            )
        validate_password_format(request.password)
        allergens = self.allergen_repository.get_by_codes(request.allergen_codes)
        if len(allergens) != len(set(request.allergen_codes)):
            raise BadRequestException(message="유효하지 않은 알레르기 코드가 있습니다.", code="INVALID_ALLERGEN_CODE", detail="allergen")
        user = self.user_repository.create(
            login_id=request.login_id,
            hashed_password=hash_password(request.password),
            name=request.name,
            student_number=request.student_number,
            role=UserRole.STUDENT,
            is_active=True,
        )
        self.allergen_repository.replace_user_allergies(user.id, [item.id for item in allergens])
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, request: LoginRequest) -> TokenPairResponse:
        user = self.user_repository.get_by_login_id(request.login_id)
        if not user or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedException(message="로그인에 실패했습니다.", code="INVALID_CREDENTIALS", detail="아이디 또는 비밀번호 불일치")
        if not user.is_active:
            raise UnauthorizedException(message="비활성화된 계정입니다.", code="INACTIVE_USER", detail=f"user_id={user.id}")
        access_token = create_access_token(user.id, user.role)
        refresh_token, expires_at = create_refresh_token(user.id)
        self.auth_repository.create_refresh_token(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires_at)
        self.db.commit()
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token_expires_in_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

    def refresh(self, request: RefreshTokenRequest) -> TokenPairResponse:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="refresh token 필요")
        token_hash = hash_token(request.refresh_token)
        refresh_token = self.auth_repository.get_refresh_token(token_hash)
        if not refresh_token or refresh_token.revoked_at is not None:
            raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="폐기된 refresh token")
        expires_at = refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise UnauthorizedException(message="토큰이 만료되었습니다.", code="TOKEN_EXPIRED", detail="refresh token 만료")
        token_user_sub = payload.get("sub")
        if not isinstance(token_user_sub, str) or token_user_sub != str(refresh_token.user_id):
            raise UnauthorizedException(message="유효하지 않은 토큰입니다.", code="INVALID_TOKEN", detail="refresh token user mismatch")
        user = self.user_repository.get_by_id(refresh_token.user_id)
        if not user:
            raise UnauthorizedException(message="사용자를 찾을 수 없습니다.", code="USER_NOT_FOUND", detail="refresh token user")
        if not user.is_active:
            raise UnauthorizedException(message="비활성화된 계정입니다.", code="INACTIVE_USER", detail=f"user_id={user.id}")
        access_token = create_access_token(user.id, user.role)
        new_refresh_token, expires_at = create_refresh_token(user.id)
        self.auth_repository.revoke_refresh_token(refresh_token, datetime.now(UTC))
        self.auth_repository.create_refresh_token(user_id=user.id, token_hash=hash_token(new_refresh_token), expires_at=expires_at)
        self.db.commit()
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            access_token_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token_expires_in_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

    def logout(self, request: LogoutRequest) -> None:
        refresh_token = self.auth_repository.get_refresh_token(hash_token(request.refresh_token))
        if refresh_token and refresh_token.revoked_at is None:
            self.auth_repository.revoke_refresh_token(refresh_token, datetime.now(UTC))
            self.db.commit()

    def change_password(self, user_id: int, request: ChangePasswordRequest) -> None:
        user = self.user_repository.get_by_id(user_id)
        if not user or not verify_password(request.current_password, user.hashed_password):
            raise UnauthorizedException(message="비밀번호 변경에 실패했습니다.", code="INVALID_CREDENTIALS", detail="현재 비밀번호 불일치")
        validate_password_format(request.new_password)
        user.hashed_password = hash_password(request.new_password)
        self.auth_repository.revoke_all_by_user_id(user_id, datetime.now(UTC))
        self.db.commit()
