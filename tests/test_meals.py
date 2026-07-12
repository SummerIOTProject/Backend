from datetime import date


def _meal_payload():
    return {
        "meal_date": str(date.today()),
        "meal_type": "LUNCH",
        "school_name": "국민대학교",
        "menu_items": [
            {"name": "쌀밥", "category": "RICE", "tray_section": 1, "display_order": 1},
            {"name": "제육볶음", "category": "MAIN_DISH", "tray_section": 2, "display_order": 2},
            {"name": "김치", "category": "SIDE_DISH", "tray_section": 3, "display_order": 3},
        ],
    }


def test_create_meal_success(client, create_account):
    admin = create_account(
        name="관리자",
        student_number="A0001",
        email="admin@example.com",
        role="ADMIN",
    )
    response = client.post("/api/v1/meals", json=_meal_payload(), headers=admin["headers"])
    assert response.status_code == 201
    assert len(response.json()["data"]["menu_items"]) == 3


def test_get_today_meals_success(client, create_account):
    admin = create_account(
        name="관리자",
        student_number="A0001",
        email="admin@example.com",
        role="ADMIN",
    )
    client.post("/api/v1/meals", json=_meal_payload(), headers=admin["headers"])
    response = client.get("/api/v1/meals/today")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] == 1
