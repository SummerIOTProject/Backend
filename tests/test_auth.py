from app.core import security
from app.models.user import User
from app.utils.enums import UserRole


def test_signup_success(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "login_id": "junseo0309",
            "password": "Password123!",
            "name": "정준서",
            "student_number": "20223137",
            "allergen_codes": ["MILK", "PEANUT"],
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["login_id"] == "junseo0309"


def test_duplicate_login_id_fail(client, create_account):
    create_account(login_id="junseo0309", student_number="20223137")
    response = client.post(
        "/api/v1/auth/signup",
        json={"login_id": "junseo0309", "password": "Password123!", "name": "다른학생", "student_number": "20223138", "allergen_codes": []},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_LOGIN_ID"


def test_duplicate_student_number_fail(client, create_account):
    create_account(login_id="junseo0309", student_number="20223137")
    response = client.post(
        "/api/v1/auth/signup",
        json={"login_id": "junseo0310", "password": "Password123!", "name": "다른학생", "student_number": "20223137", "allergen_codes": []},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_STUDENT_NUMBER"


def test_weak_password_fail(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={"login_id": "weak1", "password": "password", "name": "학생", "student_number": "20220001", "allergen_codes": []},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_PASSWORD_FORMAT"


def test_login_success(client, create_account):
    create_account(login_id="junseo0309", student_number="20223137")
    response = client.post("/api/v1/auth/login", json={"login_id": "junseo0309", "password": "Password123!"})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert "refresh_token" in response.json()["data"]


def test_login_wrong_password_fail(client, create_account):
    create_account(login_id="junseo0309", student_number="20223137")
    response = client.post("/api/v1/auth/login", json={"login_id": "junseo0309", "password": "WrongPassword1!"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_login_fail(client, create_account, db_session_factory):
    account = create_account(login_id="inactive1", student_number="20223139")
    session = db_session_factory()
    try:
        user = session.get(User, account["user_id"])
        user.is_active = False
        session.commit()
    finally:
        session.close()
    response = client.post("/api/v1/auth/login", json={"login_id": "inactive1", "password": "Password123!"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INACTIVE_USER"


def test_protected_api_without_token_fail(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401


def test_expired_access_token_fail(client, create_account, monkeypatch):
    create_account(login_id="expired1", student_number="20223140")
    original = security.settings.ACCESS_TOKEN_EXPIRE_MINUTES
    try:
        security.settings.ACCESS_TOKEN_EXPIRE_MINUTES = -1
        token = security.create_access_token(1, UserRole.STUDENT)
    finally:
        security.settings.ACCESS_TOKEN_EXPIRE_MINUTES = original
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_refresh_token_cannot_access_protected_api(client, create_account):
    account = create_account(login_id="refresh1", student_number="20223141")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {account['refresh_token']}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_refresh_rotation_and_revoked_token_fail(client, create_account):
    account = create_account(login_id="refresh2", student_number="20223142")
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": account["refresh_token"]})
    assert first.status_code == 200
    second = client.post("/api/v1/auth/refresh", json={"refresh_token": account["refresh_token"]})
    assert second.status_code == 401
    assert second.json()["error"]["code"] == "INVALID_TOKEN"


def test_password_change_revokes_all_refresh_tokens(client, create_account):
    account = create_account(login_id="refresh3", student_number="20223143")
    response = client.patch(
        "/api/v1/auth/password",
        headers=account["headers"],
        json={"current_password": "Password123!", "new_password": "NewPassword123!"},
    )
    assert response.status_code == 200
    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": account["refresh_token"]})
    assert refresh.status_code == 401
    assert refresh.json()["error"]["code"] == "INVALID_TOKEN"


def test_student_cannot_access_admin_api(client, create_account):
    student = create_account(login_id="student1", student_number="20223137")
    response = client.get("/api/v1/admin/users", headers=student["headers"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_REQUIRED"
