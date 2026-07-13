def test_register_my_rfid_success(client, create_account):
    student = create_account(login_id="student1", student_number="20223137")
    response = client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    assert response.status_code == 201
    assert response.json()["data"]["uid"] == "04A3B29C7F6180"


def test_duplicate_uid_fail(client, create_account):
    student1 = create_account(login_id="student1", student_number="20223137")
    student2 = create_account(login_id="student2", student_number="20223138")
    client.post("/api/v1/me/rfid-cards", headers=student1["headers"], json={"uid": "04A3B29C7F6180"})
    response = client.post("/api/v1/me/rfid-cards", headers=student2["headers"], json={"uid": "04A3B29C7F6180"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RFID_ALREADY_REGISTERED"


def test_deactivate_card_and_scan_fail(client, create_account, create_menu, create_meal):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"])
    create_meal(admin["headers"], [menu["id"]], meal_type="LUNCH")
    card = client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"}).json()["data"]
    deactivate = client.patch(f"/api/v1/me/rfid-cards/{card['id']}/deactivate", headers=student["headers"])
    assert deactivate.status_code == 200
    response = client.post("/api/v1/device/rfid/scan", headers={"X-Device-Key": "device-secret"}, json={"uid": "04A3B29C7F6180", "meal_type": "LUNCH"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RFID_NOT_FOUND"


def test_device_key_validation(client):
    missing = client.post("/api/v1/device/rfid/scan", json={"uid": "uid", "meal_type": "LUNCH"})
    wrong = client.post("/api/v1/device/rfid/scan", headers={"X-Device-Key": "wrong"}, json={"uid": "uid", "meal_type": "LUNCH"})
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["error"]["code"] == "INVALID_DEVICE_KEY"
    assert wrong.json()["error"]["code"] == "INVALID_DEVICE_KEY"


def test_rfid_scan_success_with_meal_type(client, create_account, create_menu, create_meal):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"])
    create_meal(admin["headers"], [menu["id"]], meal_type="LUNCH")
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    response = client.post("/api/v1/device/rfid/scan", headers={"X-Device-Key": "device-secret"}, json={"uid": "04A3B29C7F6180", "meal_type": "LUNCH"})
    assert response.status_code == 200
    assert response.json()["data"]["meal"]["meal_type"] == "LUNCH"


def test_meal_not_found_for_requested_meal_type(client, create_account, create_menu, create_meal):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"])
    create_meal(admin["headers"], [menu["id"]], meal_type="DINNER")
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    response = client.post("/api/v1/device/rfid/scan", headers={"X-Device-Key": "device-secret"}, json={"uid": "04A3B29C7F6180", "meal_type": "LUNCH"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"


def test_inactive_user_scan_fail(client, create_account, create_menu, create_meal, db_session_factory):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"])
    create_meal(admin["headers"], [menu["id"]], meal_type="LUNCH")
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    session = db_session_factory()
    try:
        from app.models.user import User

        user = session.get(User, student["user_id"])
        user.is_active = False
        session.commit()
    finally:
        session.close()
    response = client.post("/api/v1/device/rfid/scan", headers={"X-Device-Key": "device-secret"}, json={"uid": "04A3B29C7F6180", "meal_type": "LUNCH"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RFID_NOT_FOUND"
