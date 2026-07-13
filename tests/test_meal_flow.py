def _prepare_flow(client, create_account, create_menu, create_meal):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"])
    meal = create_meal(admin["headers"], [menu["id"]])
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    return student, meal, admin


def test_create_meal_record_by_rfid(client, create_account, create_menu, create_meal):
    _, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    response = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]})
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "CREATED"


def test_duplicate_meal_record_blocked(client, create_account, create_menu, create_meal):
    _, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]})
    response = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_MEAL_RECORD"


def test_image_upload_and_protected_image_access(client, create_account, create_menu, create_meal, sample_image_file):
    student, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    before = client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    after = client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    assert before.status_code == 201
    assert after.status_code == 201
    images = client.get(f"/api/v1/me/meal-records/{record['id']}/images", headers=student["headers"]).json()["data"]
    image_response = client.get(images[0]["image_url"], headers=student["headers"])
    assert image_response.status_code == 200


def test_png_and_webp_upload_success(client, create_account, create_menu, create_meal, sample_png_file, sample_webp_file):
    student, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    png = client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_png_file})
    webp = client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_webp_file})
    assert png.status_code == 201
    assert webp.status_code == 201


def test_fake_jpg_fail(client, create_account, create_menu, create_meal):
    student, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    fake = ("fake.jpg", b"not-an-image", "image/jpeg")
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": fake})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE_FORMAT"


def test_other_student_image_upload_forbidden(client, create_account, create_menu, create_meal, sample_image_file):
    _, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    other = create_account(login_id="student2", student_number="20223138")
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=other["headers"], files={"file": sample_image_file})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_RESOURCE"
