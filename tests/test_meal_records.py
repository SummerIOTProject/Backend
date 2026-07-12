from datetime import date


def prepare_user_and_meal(client, create_account):
    user = create_account(name="정준서", student_number="20223137", email="junseo@example.com")
    admin = create_account(name="관리자", student_number="A0001", email="admin@example.com", role="ADMIN")
    meal_id = client.post(
        "/api/v1/meals",
        json={
            "meal_date": str(date.today()),
            "meal_type": "LUNCH",
            "school_name": "국민대학교",
            "menu_items": [
                {"name": "쌀밥", "category": "RICE", "tray_section": 1, "display_order": 1},
                {"name": "제육볶음", "category": "MAIN_DISH", "tray_section": 2, "display_order": 2},
            ],
        },
        headers=admin["headers"],
    ).json()["data"]["id"]
    return user, meal_id


def test_create_meal_record_success(client, create_account):
    user, meal_id = prepare_user_and_meal(client, create_account)
    response = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id})
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "CREATED"


def test_duplicate_meal_record_blocked(client, create_account):
    user, meal_id = prepare_user_and_meal(client, create_account)
    client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id})
    response = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_MEAL_RECORD"


def test_upload_before_and_after_images(client, create_account, sample_image_file):
    user, meal_id = prepare_user_and_meal(client, create_account)
    record_id = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id}).json()["data"]["id"]

    before_response = client.post(
        f"/api/v1/meal-records/{record_id}/images/before",
        files={"file": sample_image_file},
    )
    assert before_response.status_code == 201
    assert before_response.json()["data"]["image_type"] == "BEFORE"


def test_upload_after_without_before_fails(client, create_account, sample_image_file):
    user, meal_id = prepare_user_and_meal(client, create_account)
    record_id = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id}).json()["data"]["id"]
    response = client.post(f"/api/v1/meal-records/{record_id}/images/after", files={"file": sample_image_file})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BEFORE_IMAGE_REQUIRED"


def test_upload_after_image_success(client, create_account, sample_image_file):
    user, meal_id = prepare_user_and_meal(client, create_account)
    record_id = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id}).json()["data"]["id"]
    client.post(f"/api/v1/meal-records/{record_id}/images/before", files={"file": sample_image_file})
    response = client.post(f"/api/v1/meal-records/{record_id}/images/after", files={"file": sample_image_file})
    assert response.status_code == 201
    assert response.json()["data"]["image_type"] == "AFTER"
