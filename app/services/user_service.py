from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdateRequest


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)

    def get_user(self, user_id: int):
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="사용자를 찾을 수 없습니다.", code="USER_NOT_FOUND", detail=f"user_id={user_id}")
        return user

    def update_me(self, user_id: int, request: UserUpdateRequest):
        user = self.get_user(user_id)
        if request.login_id and request.login_id != user.login_id:
            if self.user_repository.get_by_login_id(request.login_id):
                raise ConflictException(message="이미 사용 중인 로그인 ID입니다.", code="DUPLICATE_LOGIN_ID", detail=request.login_id)
        payload = request.model_dump(exclude_unset=True)
        self.user_repository.update(user, **payload)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_active_students(self):
        return self.user_repository.list_active_students()

    def list_users(self, *, page: int, size: int, keyword: str | None, is_active: bool | None):
        return self.user_repository.list_users(page=page, size=size, keyword=keyword, is_active=is_active)
