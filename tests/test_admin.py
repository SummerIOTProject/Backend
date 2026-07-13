from app.utils.datetime import today_local


def test_admin_users_pagination_and_keyword(client, create_account):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    create_account(login_id="student1", student_number="20223137", name="홍길동")
    create_account(login_id="student2", student_number="20223138", name="김철수")
    response = client.get("/api/v1/admin/users?page=1&size=1&keyword=student1", headers=admin["headers"])
    assert response.status_code == 200
    assert response.json()["data"]["size"] == 1


def test_admin_dashboard_and_leftover_summary(client, create_account, create_menu, create_meal, sample_image_file):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menus = [
        create_menu(admin["headers"], name="제육볶음"),
        create_menu(admin["headers"], name="김치볶음"),
        create_menu(admin["headers"], name="계란말이", allergen_codes=["EGGS"]),
        create_menu(admin["headers"], name="멸치볶음", allergen_codes=[]),
        create_menu(admin["headers"], name="미역국", allergen_codes=[]),
    ]
    meal = create_meal(admin["headers"], [menu["id"] for menu in menus])
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    dashboard = client.get(f"/api/v1/admin/dashboard?date={meal['meal_date']}", headers=admin["headers"])
    summary = client.get(f"/api/v1/admin/leftover-summary?start_date={meal['meal_date']}&end_date={meal['meal_date']}", headers=admin["headers"])
    assert dashboard.status_code == 200
    assert summary.status_code == 200
    assert dashboard.json()["data"]["active_user_count"] == 1
    assert dashboard.json()["data"]["meal_record_count"] == 1
    assert dashboard.json()["data"]["completed_analysis_count"] == 1
    assert dashboard.json()["data"]["analysis_sample_count"] == 5
    assert summary.json()["data"][0]["menu_name"] == "제육볶음"


def test_admin_dashboard_no_analysis_returns_null_averages(client, create_account):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    response = client.get(f"/api/v1/admin/dashboard?date={today_local().isoformat()}", headers=admin["headers"])
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["completed_analysis_count"] == 0
    assert body["failed_analysis_count"] == 0
    assert body["analysis_sample_count"] == 0
    assert body["average_consumed_ratio"] is None
    assert body["average_leftover_ratio"] is None
