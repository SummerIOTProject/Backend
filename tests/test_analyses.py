from datetime import date


def bootstrap_record(client, create_account, sample_image_file):
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
                {"name": "김치", "category": "SIDE_DISH", "tray_section": 3, "display_order": 3},
            ],
        },
        headers=admin["headers"],
    ).json()["data"]["id"]
    record_id = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id}).json()["data"]["id"]
    client.post(f"/api/v1/meal-records/{record_id}/images/before", files={"file": sample_image_file})
    client.post(f"/api/v1/meal-records/{record_id}/images/after", files={"file": sample_image_file})
    return user, meal_id, record_id


def test_mock_analysis_success(client, create_account, sample_image_file):
    _, _, record_id = bootstrap_record(client, create_account, sample_image_file)
    response = client.post(f"/api/v1/meal-records/{record_id}/analyze", json={"analysis_type": "MOCK"})
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 3


def test_get_analysis_result(client, create_account, sample_image_file):
    _, _, record_id = bootstrap_record(client, create_account, sample_image_file)
    client.post(f"/api/v1/meal-records/{record_id}/analyze", json={"analysis_type": "MOCK"})
    response = client.get(f"/api/v1/meal-records/{record_id}/analysis")
    assert response.status_code == 200
    assert response.json()["data"]["meal_record_id"] == record_id


def test_get_recommendations(client, create_account, sample_image_file):
    user, meal_id, record_id = bootstrap_record(client, create_account, sample_image_file)
    client.post(f"/api/v1/meal-records/{record_id}/analyze", json={"analysis_type": "MOCK"})
    response = client.get(
        "/api/v1/me/recommendations",
        params={"meal_id": meal_id},
        headers=user["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 3
