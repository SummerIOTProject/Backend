from __future__ import annotations

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.security import verify_password
from app.models.user import User
from app.utils.enums import UserRole
from scripts import create_admin


def _make_user(session, *, login_id: str, student_number: str, role: UserRole = UserRole.STUDENT, is_active: bool = True, name: str = "학생", hashed_password: str = "old-hash") -> User:
    user = User(
        login_id=login_id,
        hashed_password=hashed_password,
        name=name,
        student_number=student_number,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    return user


def test_create_admin_success(db_session_factory):
    session = db_session_factory()
    try:
        message = create_admin.create_or_update_admin(
            session,
            login_id="admin",
            name="관리자",
            student_number="ADMIN001",
            password="AdminPassword123!",
            update_existing=False,
        )
        stored = session.query(User).filter(User.login_id == "admin").one()
        assert message == "관리자 계정이 생성되었습니다. login_id=admin"
        assert stored.role == UserRole.ADMIN
        assert stored.is_active is True
        assert stored.hashed_password != "AdminPassword123!"
        assert verify_password("AdminPassword123!", stored.hashed_password) is True
    finally:
        session.close()


def test_password_mismatch_exits_without_db_work(capsys):
    called = False

    def fake_session_factory():
        nonlocal called
        called = True
        raise AssertionError("session factory should not be called")

    responses = iter(["AdminPassword123!", "DifferentPassword123!"])
    rc = create_admin.main(
        ["--login-id", "admin", "--name", "관리자", "--student-number", "ADMIN001"],
        session_factory=fake_session_factory,
        getpass_fn=lambda _prompt: next(responses),
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "비밀번호가 일치하지 않습니다." in captured.err
    assert called is False


def test_empty_password_rejected_without_db_work(capsys):
    called = False

    def fake_session_factory():
        nonlocal called
        called = True
        raise AssertionError("session factory should not be called")

    rc = create_admin.main(
        ["--login-id", "admin", "--name", "관리자", "--student-number", "ADMIN001"],
        session_factory=fake_session_factory,
        getpass_fn=lambda _prompt: "",
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "비밀번호는 비워둘 수 없습니다." in captured.err
    assert called is False


def test_existing_login_id_requires_update_existing(db_session_factory):
    session = db_session_factory()
    try:
        original = _make_user(session, login_id="admin", student_number="ADMIN000")
        try:
            create_admin.create_or_update_admin(
                session,
                login_id="admin",
                name="관리자",
                student_number="ADMIN001",
                password="AdminPassword123!",
                update_existing=False,
            )
        except ValueError as exc:
            assert str(exc) == "동일한 login_id의 계정이 이미 존재합니다. --update-existing 옵션을 사용하세요."
        else:
            raise AssertionError("expected ValueError")

        session.refresh(original)
        assert original.role == UserRole.STUDENT
        assert original.student_number == "ADMIN000"
    finally:
        session.close()


def test_update_existing_promotes_same_login_id_to_admin(db_session_factory):
    session = db_session_factory()
    try:
        user = _make_user(
            session,
            login_id="admin",
            student_number="OLD001",
            role=UserRole.STUDENT,
            is_active=False,
            name="기존사용자",
        )
        message = create_admin.create_or_update_admin(
            session,
            login_id="admin",
            name="관리자",
            student_number="ADMIN001",
            password="AdminPassword123!",
            update_existing=True,
        )

        session.refresh(user)
        assert message == "기존 계정을 관리자 계정으로 갱신했습니다. login_id=admin"
        assert user.name == "관리자"
        assert user.student_number == "ADMIN001"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
        assert user.hashed_password != "AdminPassword123!"
        assert verify_password("AdminPassword123!", user.hashed_password) is True
    finally:
        session.close()


def test_duplicate_student_number_with_other_account_fails(db_session_factory):
    session = db_session_factory()
    try:
        _make_user(session, login_id="admin", student_number="ADMIN000")
        other = _make_user(session, login_id="student1", student_number="ADMIN001")
        try:
            create_admin.create_or_update_admin(
                session,
                login_id="admin",
                name="관리자",
                student_number="ADMIN001",
                password="AdminPassword123!",
                update_existing=True,
            )
        except ValueError as exc:
            assert str(exc) == "해당 학번을 사용하는 계정이 이미 존재합니다."
        else:
            raise AssertionError("expected ValueError")

        session.refresh(other)
        assert other.login_id == "student1"
        assert other.role == UserRole.STUDENT
    finally:
        session.close()


def test_existing_student_number_account_is_not_auto_promoted(db_session_factory):
    session = db_session_factory()
    try:
        existing = _make_user(session, login_id="student1", student_number="ADMIN001", role=UserRole.STUDENT, name="학생계정")
        try:
            create_admin.create_or_update_admin(
                session,
                login_id="admin",
                name="관리자",
                student_number="ADMIN001",
                password="AdminPassword123!",
                update_existing=False,
            )
        except ValueError as exc:
            assert str(exc) == "해당 학번을 사용하는 계정이 이미 존재합니다."
        else:
            raise AssertionError("expected ValueError")

        session.refresh(existing)
        assert existing.login_id == "student1"
        assert existing.name == "학생계정"
        assert existing.role == UserRole.STUDENT
    finally:
        session.close()


def test_integrity_error_triggers_rollback(capsys, monkeypatch):
    class FakeSession:
        def __init__(self):
            self.rollback_called = 0
            self.close_called = 0

        def rollback(self):
            self.rollback_called += 1

        def close(self):
            self.close_called += 1

    fake_session = FakeSession()
    monkeypatch.setattr(
        create_admin,
        "create_or_update_admin",
        lambda *args, **kwargs: (_ for _ in ()).throw(IntegrityError("stmt", {}, Exception("dup"))),
    )

    rc = create_admin.main(
        ["--login-id", "admin", "--name", "관리자", "--student-number", "ADMIN001"],
        session_factory=lambda: fake_session,
        getpass_fn=lambda _prompt: "AdminPassword123!",
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "관리자 생성 실패: 로그인 아이디 또는 학번이 이미 존재합니다." in captured.err
    assert fake_session.rollback_called == 1
    assert fake_session.close_called == 1


def test_sqlalchemy_error_triggers_rollback_without_sensitive_details(capsys, monkeypatch):
    class FakeSession:
        def __init__(self):
            self.rollback_called = 0
            self.close_called = 0

        def rollback(self):
            self.rollback_called += 1

        def close(self):
            self.close_called += 1

    fake_session = FakeSession()

    def raise_sqlalchemy_error(*args, **kwargs):
        raise SQLAlchemyError("postgresql://secret-user:secret-pass@host/db")

    monkeypatch.setattr(create_admin, "create_or_update_admin", raise_sqlalchemy_error)

    rc = create_admin.main(
        ["--login-id", "admin", "--name", "관리자", "--student-number", "ADMIN001"],
        session_factory=lambda: fake_session,
        getpass_fn=lambda _prompt: "AdminPassword123!",
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "관리자 생성 실패: DB 오류(SQLAlchemyError)" in captured.err
    assert "secret-pass" not in captured.err
    assert "postgresql://" not in captured.err
    assert fake_session.rollback_called == 1
    assert fake_session.close_called == 1
