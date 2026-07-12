from datetime import date


def test_get_my_profile_success(client, create_account):
    user = create_account(name="정준서", student_number="20223137", email="junseo@example.com")
    response = client.get("/api/v1/me", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "junseo@example.com"


def test_my_recommendations_success(client, create_account, sample_image_file):
    user = create_account(name="정준서", student_number="20223137", email="junseo@example.com")
    admin = create_account(name="관리자", student_number="A0001", email="admin@example.com", role="ADMIN")
    meal_response = client.post(
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
    )
    meal_id = meal_response.json()["data"]["id"]
    record_id = client.post("/api/v1/meal-records", json={"user_id": user["user_id"], "meal_id": meal_id}).json()["data"]["id"]
    client.post(f"/api/v1/meal-records/{record_id}/images/before", files={"file": sample_image_file})
    client.post(f"/api/v1/meal-records/{record_id}/images/after", files={"file": sample_image_file})
    client.post(f"/api/v1/meal-records/{record_id}/analyze", json={"analysis_type": "MOCK"})

    response = client.get("/api/v1/me/recommendations", params={"meal_id": meal_id}, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == user["user_id"]
