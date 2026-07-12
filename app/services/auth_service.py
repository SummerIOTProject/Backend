from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, SignUpRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)

    def signup(self, request: SignUpRequest):
        if self.user_repository.get_by_student_number(request.student_number):
            raise ConflictException(
                message="이미 등록된 학번입니다.",
                code="DUPLICATE_STUDENT_NUMBER",
                detail=f"student_number={request.student_number}",
            )
        if self.user_repository.get_by_email(request.email):
            raise ConflictException(
                message="이미 등록된 이메일입니다.",
                code="DUPLICATE_EMAIL",
                detail=f"email={request.email}",
            )
        user = self.user_repository.create(
            name=request.name,
            student_number=request.student_number,
            email=request.email,
            hashed_password=hash_password(request.password),
            role="STUDENT",
            is_active=True,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, request: LoginRequest) -> TokenResponse:
        user = self.user_repository.get_by_email(request.email)
        if not user or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedException(
                message="로그인에 실패했습니다.",
                code="INVALID_CREDENTIALS",
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )
        if not user.is_active:
            raise UnauthorizedException(
                message="비활성화된 계정입니다.",
                code="INACTIVE_USER",
                detail=f"user_id={user.id}",
            )
        token = create_access_token(user_id=user.id, role=user.role)
        return TokenResponse(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def change_password(self, user_id: int, request: ChangePasswordRequest) -> None:
        user = self.user_repository.get_by_id(user_id)
        if not user or not verify_password(request.current_password, user.hashed_password):
            raise UnauthorizedException(
                message="비밀번호 변경에 실패했습니다.",
                code="INVALID_CREDENTIALS",
                detail="현재 비밀번호가 올바르지 않습니다.",
            )
        user.hashed_password = hash_password(request.new_password)
        self.db.commit()

    def refresh_access_token(self, user_id: int, role: str) -> TokenResponse:
        token = create_access_token(user_id=user_id, role=role)
        return TokenResponse(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
