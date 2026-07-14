from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.enums import UserRole


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update an admin account.")
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--student-number", required=True)
    parser.add_argument("--update-existing", action="store_true")
    return parser.parse_args(argv)


def prompt_admin_password(getpass_fn: Callable[[str], str] = getpass.getpass) -> str:
    password = getpass_fn("관리자 비밀번호: ")
    if not password:
        raise ValueError("비밀번호는 비워둘 수 없습니다.")
    password_confirm = getpass_fn("관리자 비밀번호 확인: ")
    if password != password_confirm:
        raise ValueError("비밀번호가 일치하지 않습니다.")
    return password


def create_or_update_admin(
    db: Session,
    *,
    login_id: str,
    name: str,
    student_number: str,
    password: str,
    update_existing: bool,
) -> str:
    repo = UserRepository(db)
    existing_login_user = repo.get_by_login_id(login_id)
    existing_student_number_user = repo.get_by_student_number(student_number)
    hashed_password = hash_password(password)

    if existing_login_user:
        if not update_existing:
            raise ValueError("동일한 login_id의 계정이 이미 존재합니다. --update-existing 옵션을 사용하세요.")
        if existing_student_number_user and existing_student_number_user.id != existing_login_user.id:
            raise ValueError("해당 학번을 사용하는 계정이 이미 존재합니다.")
        existing_login_user.hashed_password = hashed_password
        existing_login_user.name = name
        existing_login_user.student_number = student_number
        existing_login_user.role = UserRole.ADMIN
        existing_login_user.is_active = True
        db.commit()
        return f"기존 계정을 관리자 계정으로 갱신했습니다. login_id={existing_login_user.login_id}"

    if existing_student_number_user:
        raise ValueError("해당 학번을 사용하는 계정이 이미 존재합니다.")

    user = User(
        login_id=login_id,
        hashed_password=hashed_password,
        name=name,
        student_number=student_number,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return f"관리자 계정이 생성되었습니다. login_id={user.login_id}"


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    getpass_fn: Callable[[str], str] = getpass.getpass,
) -> int:
    args = parse_args(argv)
    try:
        password = prompt_admin_password(getpass_fn)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    db = session_factory()
    try:
        message = create_or_update_admin(
            db,
            login_id=args.login_id,
            name=args.name,
            student_number=args.student_number,
            password=password,
            update_existing=args.update_existing,
        )
        print(message)
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except IntegrityError:
        db.rollback()
        print("관리자 생성 실패: 로그인 아이디 또는 학번이 이미 존재합니다.", file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"관리자 생성 실패: DB 오류({type(exc).__name__})", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
