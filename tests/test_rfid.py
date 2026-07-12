def test_register_rfid_success(client, create_account):
    user = create_account(name="정준서", student_number="20223137", email="junseo@example.com")
    response = client.post(
        "/api/v1/rfid-cards",
        json={"user_id": user["user_id"], "uid": "04A3B29C7F6180"},
        headers=user["headers"],
    )
    assert response.status_code == 201
    assert response.json()["data"]["uid"] == "04A3B29C7F6180"


def test_duplicate_rfid_uid(client, create_account):
    user_1 = create_account(name="정준서", student_number="20223137", email="junseo@example.com")
    user_2 = create_account(name="홍길동", student_number="20223138", email="hong@example.com")
    client.post(
        "/api/v1/rfid-cards",
        json={"user_id": user_1["user_id"], "uid": "04A3B29C7F6180"},
        headers=user_1["headers"],
    )
    response = client.post(
        "/api/v1/rfid-cards",
        json={"user_id": user_2["user_id"], "uid": "04A3B29C7F6180"},
        headers=user_2["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_RFID_UID"
