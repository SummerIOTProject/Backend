from __future__ import annotations

import argparse
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_format
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.enums import UserRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an admin account.")
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--student-number", required=True)
    parser.add_argument("--password", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_password_format(args.password)
    except Exception as exc:
        print(f"관리자 생성 실패: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.get_by_login_id(args.login_id):
            print("관리자 생성 실패: 이미 사용 중인 login_id입니다.", file=sys.stderr)
            return 1
        if repo.get_by_student_number(args.student_number):
            print("관리자 생성 실패: 이미 사용 중인 student_number입니다.", file=sys.stderr)
            return 1
        user = User(
            login_id=args.login_id,
            hashed_password=hash_password(args.password),
            name=args.name,
            student_number=args.student_number,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"관리자 계정이 생성되었습니다. login_id={user.login_id}")
        return 0
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"관리자 생성 실패: DB 오류({type(exc).__name__})", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
