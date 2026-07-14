def test_allergen_seed_count_and_codes(client):
    response = client.get("/api/v1/allergens")
    assert response.status_code == 200
    items = response.json()["data"]
    codes = [item["code"] for item in items]
    assert len(items) == 19
    assert "PINE_NUT" in codes
    assert "EGGS" in codes
    assert "SULFITES" in codes
    assert "EGG" not in codes
    assert "SULFITE" not in codes


def test_update_my_allergies(client, create_account):
    student = create_account(login_id="student1", student_number="20223137")
    response = client.put("/api/v1/me/allergens", headers=student["headers"], json={"allergen_codes": ["MILK", "SHRIMP", "PINE_NUT"]})
    assert response.status_code == 200
    codes = [item["code"] for item in response.json()["data"]["items"]]
    assert set(codes) == {"MILK", "SHRIMP", "PINE_NUT"}


def test_allergy_intersection_restriction(client, create_account, create_menu, create_meal):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137", allergen_codes=["MILK", "PEANUT"])
    menu = create_menu(admin["headers"], name="우유죽", allergen_codes=["MILK"])
    create_meal(admin["headers"], [menu["id"]], meal_type="LUNCH")
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    response = client.post(
        "/api/v1/device/rfid/scan",
        headers={"X-Device-Key": "device-secret"},
        json={"uid": "04A3B29C7F6180", "meal_type": "LUNCH"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["menu_guidance"][0]["is_restricted"] is True
