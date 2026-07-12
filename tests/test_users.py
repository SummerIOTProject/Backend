def test_create_user_success(client):
    response = client.post(
        "/api/v1/users",
        json={
            "name": "정준서",
            "student_number": "20223137",
            "email": "junseo@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["student_number"] == "20223137"


def test_duplicate_student_number(client):
    payload = {
        "name": "정준서",
        "student_number": "20223137",
        "email": "junseo@example.com",
        "password": "Password123",
    }
    client.post("/api/v1/users", json=payload)
    response = client.post("/api/v1/users", json={**payload, "email": "junseo2@example.com"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_STUDENT_NUMBER"
