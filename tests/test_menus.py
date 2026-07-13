from app.schemas.menu import MenuCreateRequest


def test_menu_create_and_detail(client, create_account, create_menu):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    menu = create_menu(admin["headers"])
    detail = client.get(f"/api/v1/menus/{menu['id']}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["name"] == "제육볶음"
    assert "돼지고기" in body["ingredients"]
    assert "SOYBEAN" in body["allergen_codes"]


def test_menu_validation_negative_nutrition_fail(client, create_account):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    response = client.post(
        "/api/v1/admin/menus",
        headers=admin["headers"],
        json={
            "name": "오류메뉴",
            "standard_serving_g": 120,
            "nutrition_per_100g": {"calories_kcal": -1, "carbohydrate_g": 1, "protein_g": 1, "fat_g": 1},
            "ingredients": ["쌀"],
            "allergen_codes": [],
        },
    )
    assert response.status_code == 422


def test_menu_validation_zero_serving_fail(client, create_account):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    response = client.post(
        "/api/v1/admin/menus",
        headers=admin["headers"],
        json={
            "name": "오류메뉴2",
            "standard_serving_g": 0,
            "nutrition_per_100g": {"calories_kcal": 1, "carbohydrate_g": 1, "protein_g": 1, "fat_g": 1},
            "ingredients": ["쌀"],
            "allergen_codes": [],
        },
    )
    assert response.status_code == 422


def test_inactive_menu_cannot_be_used_in_meal(client, create_account, create_menu):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    menu = create_menu(admin["headers"])
    client.delete(f"/api/v1/admin/menus/{menu['id']}", headers=admin["headers"])
    response = client.post(
        "/api/v1/admin/meals",
        headers=admin["headers"],
        json={"meal_date": "2026-07-13", "meal_type": "LUNCH", "school_name": "국민대학교", "menu_ids": [menu["id"]]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MENU_INACTIVE"


def test_menu_schema_has_no_category_or_tray_section():
    assert "category" not in MenuCreateRequest.model_fields
    assert "tray_section" not in MenuCreateRequest.model_fields
    assert "display_order" not in MenuCreateRequest.model_fields
