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
    menu = create_menu(admin["headers"])
    meal = create_meal(admin["headers"], [menu["id"]])
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    dashboard = client.get(f"/api/v1/admin/dashboard?date={meal['meal_date']}", headers=admin["headers"])
    summary = client.get(f"/api/v1/admin/leftover-summary?start_date={meal['meal_date']}&end_date={meal['meal_date']}", headers=admin["headers"])
    assert dashboard.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["data"][0]["menu_name"] == "제육볶음"
