import secrets

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserUpdateRequest


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)

    def create_user(self, request: UserCreateRequest):
        existing = self.user_repository.get_by_student_number(request.student_number)
        if existing:
            raise ConflictException(
                message="이미 등록된 학번입니다.",
                code="DUPLICATE_STUDENT_NUMBER",
                detail=f"student_number={request.student_number}",
            )
        email = request.email or f"{request.student_number}@example.com"
        email_owner = self.user_repository.get_by_email(email)
        if email_owner:
            raise ConflictException(
                message="이미 등록된 이메일입니다.",
                code="DUPLICATE_EMAIL",
                detail=f"email={email}",
            )
        password = request.password or secrets.token_urlsafe(16)
        user = self.user_repository.create(
            name=request.name,
            student_number=request.student_number,
            email=email,
            hashed_password=hash_password(password),
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message="사용자를 찾을 수 없습니다.",
                code="USER_NOT_FOUND",
                detail=f"user_id={user_id}에 해당하는 사용자가 없습니다.",
            )
        return user

    def list_users(self):
        return self.user_repository.list()

    def update_user(self, user_id: int, request: UserUpdateRequest):
        user = self.get_user(user_id)
        if request.student_number and request.student_number != user.student_number:
            existing = self.user_repository.get_by_student_number(request.student_number)
            if existing:
                raise ConflictException(
                    message="이미 등록된 학번입니다.",
                    code="DUPLICATE_STUDENT_NUMBER",
                    detail=f"student_number={request.student_number}",
                )
        if request.email and request.email != user.email:
            existing = self.user_repository.get_by_email(request.email)
            if existing:
                raise ConflictException(
                    message="이미 등록된 이메일입니다.",
                    code="DUPLICATE_EMAIL",
                    detail=f"email={request.email}",
                )
        payload = request.model_dump(exclude_unset=True)
        updated = self.user_repository.update(user, **payload)
        self.db.commit()
        self.db.refresh(updated)
        return updated
