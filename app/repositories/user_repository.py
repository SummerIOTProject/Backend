from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.user_allergy import UserAllergy
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.allergies).joinedload(UserAllergy.allergen))
            .where(User.id == user_id)
        )
        return self.db.scalars(stmt).unique().one_or_none()

    def get_by_login_id(self, login_id: str) -> User | None:
        stmt = select(User).where(User.login_id == login_id)
        return self.db.scalar(stmt)

    def get_by_student_number(self, student_number: str) -> User | None:
        stmt = select(User).where(User.student_number == student_number)
        return self.db.scalar(stmt)

    def list_active_students(self) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True)).order_by(User.id.asc())
        return list(self.db.scalars(stmt).all())

    def list_users(self, *, page: int, size: int, keyword: str | None = None, is_active: bool | None = None) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if keyword:
            pattern = f"%{keyword.lower()}%"
            filter_expr = or_(
                func.lower(User.name).like(pattern),
                func.lower(User.login_id).like(pattern),
                func.lower(User.student_number).like(pattern),
            )
            stmt = stmt.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
            count_stmt = count_stmt.where(User.is_active.is_(is_active))
        total = int(self.db.scalar(count_stmt) or 0)
        items = list(self.db.scalars(stmt.order_by(User.id.asc()).offset((page - 1) * size).limit(size)).all())
        return items, total

    def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        self.db.flush()
        return user
