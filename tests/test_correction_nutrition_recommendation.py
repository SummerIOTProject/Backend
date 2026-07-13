def _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"], name="제육볶음")
    meal = create_meal(admin["headers"], [menu["id"]])
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    analysis = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"]).json()["data"]
    return student, meal, record, analysis


def test_correct_consumed_ratio_success_and_confidence_null(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, _, analysis = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    item_id = analysis["items"][0]["id"]
    response = client.patch(f"/api/v1/me/meal-item-records/{item_id}/consumed-ratio", headers=student["headers"], json={"consumed_ratio": 0.7})
    assert response.status_code == 200
    assert response.json()["data"]["consumption_level"] == "MOST"
    assert response.json()["data"]["confidence"] is None


def test_other_student_cannot_correct(client, create_account, create_menu, create_meal, sample_image_file):
    _, _, _, analysis = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    other = create_account(login_id="student2", student_number="20223138")
    item_id = analysis["items"][0]["id"]
    response = client.patch(f"/api/v1/me/meal-item-records/{item_id}/consumed-ratio", headers=other["headers"], json={"consumed_ratio": 0.7})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_RESOURCE"


def test_invalid_consumed_ratio_fail(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, _, analysis = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    item_id = analysis["items"][0]["id"]
    response = client.patch(f"/api/v1/me/meal-item-records/{item_id}/consumed-ratio", headers=student["headers"], json={"consumed_ratio": 1.2})
    assert response.status_code == 422


def test_recent_records_and_nutrition(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, _, _ = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    response = client.get("/api/v1/me/meal-records/recent?days=5", headers=student["headers"])
    assert response.status_code == 200
    item = response.json()["data"]["items"][0]["item_records"][0]
    assert item["nutrition"]["is_estimated"] is True
    assert "calories_kcal" in item["nutrition"]


def test_recent_records_date_boundary_and_completed_only(client, create_account, create_menu, make_completed_record):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu = create_menu(admin["headers"], name="경계메뉴")
    make_completed_record(user_id=student["user_id"], menu_id=menu["id"], days_ago=0, consumed_ratio=0.5)
    make_completed_record(user_id=student["user_id"], menu_id=menu["id"], days_ago=4, consumed_ratio=0.6)
    make_completed_record(user_id=student["user_id"], menu_id=menu["id"], days_ago=5, consumed_ratio=0.7)
    make_completed_record(user_id=student["user_id"], menu_id=menu["id"], days_ago=1, consumed_ratio=0.8, status="CREATED")
    response = client.get("/api/v1/me/meal-records/recent?days=5", headers=student["headers"])
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 2


def test_recommendation_reflects_corrected_ratio_and_sample_count(client, create_account, create_menu, create_meal, sample_image_file):
    student, meal, _, analysis = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    item_id = analysis["items"][0]["id"]
    client.patch(f"/api/v1/me/meal-item-records/{item_id}/consumed-ratio", headers=student["headers"], json={"consumed_ratio": 0.2})
    response = client.get(f"/api/v1/me/recommendations?meal_id={meal['id']}", headers=student["headers"])
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["recommendation_level"] == "LESS"
    assert response.json()["data"]["items"][0]["sample_count"] == 1


def test_reanalyze_blocked_when_corrected(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, record, analysis = _analyzed_record(client, create_account, create_menu, create_meal, sample_image_file)
    item_id = analysis["items"][0]["id"]
    client.patch(f"/api/v1/me/meal-item-records/{item_id}/consumed-ratio", headers=student["headers"], json={"consumed_ratio": 0.3})
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/reanalyze", headers=student["headers"])
    assert response.status_code == 409
