import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    from app.core.config import settings

    settings.UPLOAD_DIR = str(upload_dir)
    settings.ADMIN_API_KEY = "admin-secret"

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.testing_session_local = TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_image_file():
    return ("sample.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 1024), "image/jpeg")


@pytest.fixture()
def create_account(client):
    def _create_account(
        *,
        name: str,
        student_number: str,
        email: str,
        password: str = "Password123",
        role: str = "STUDENT",
    ):
        signup_response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": name,
                "student_number": student_number,
                "email": email,
                "password": password,
            },
        )
        assert signup_response.status_code == 201
        user_id = signup_response.json()["data"]["user_id"]

        if role != "STUDENT":
            session = client.app.state.testing_session_local()
            try:
                user = session.get(User, user_id)
                user.role = role
                session.commit()
            finally:
                session.close()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]
        return {
            "user_id": user_id,
            "email": email,
            "password": password,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _create_account
