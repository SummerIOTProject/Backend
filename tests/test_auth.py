def test_signup_login_and_me_flow(client):
    signup_payload = {
        "name": "정준서",
        "student_number": "20223137",
        "email": "junseo@example.com",
        "password": "Password123",
    }
    signup_response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    signup_body = signup_response.json()
    assert signup_body["data"]["email"] == "junseo@example.com"
    assert signup_body["data"]["role"] == "STUDENT"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "junseo@example.com", "password": "Password123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    token = login_body["data"]["access_token"]
    assert token
    assert login_body["data"]["token_type"] == "bearer"

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["data"]["email"] == "junseo@example.com"
    assert me_body["data"]["student_number"] == "20223137"


def test_signup_rejects_duplicate_email(client):
    payload = {
        "name": "정준서",
        "student_number": "20223137",
        "email": "junseo@example.com",
        "password": "Password123",
    }
    client.post("/api/v1/auth/signup", json=payload)
    response = client.post(
        "/api/v1/auth/signup",
        json={**payload, "student_number": "20223138"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_EMAIL"


def test_me_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_change_password_success(client):
    signup_payload = {
        "name": "정준서",
        "student_number": "20223137",
        "email": "junseo@example.com",
        "password": "Password123",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "junseo@example.com", "password": "Password123"},
    )
    token = login_response.json()["data"]["access_token"]

    response = client.patch(
        "/api/v1/auth/password",
        json={"current_password": "Password123", "new_password": "Password456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "junseo@example.com", "password": "Password456"},
    )
    assert new_login_response.status_code == 200
