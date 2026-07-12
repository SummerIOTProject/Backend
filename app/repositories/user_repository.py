from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        name: str,
        student_number: str,
        email: str,
        hashed_password: str,
        role: str = "STUDENT",
        is_active: bool = True,
    ) -> User:
        user = User(
            name=name,
            student_number=student_number,
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_student_number(self, student_number: str) -> User | None:
        stmt = select(User).where(User.student_number == student_number)
        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def list(self) -> list[User]:
        stmt = select(User).order_by(User.id.asc())
        return list(self.db.scalars(stmt).all())

    def update(self, user: User, **kwargs: object) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        self.db.flush()
        return user
