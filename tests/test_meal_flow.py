from pathlib import Path
from datetime import timedelta

from app.core.config import settings
from app.models.meal_item_record import MealItemRecord
from app.models.meal_record import MealRecord
from app.utils.datetime import today_local


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
    assert response.json()["error"]["code"] == "MEAL_RECORD_ALREADY_EXISTS"


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


def test_image_file_missing_returns_404(client, create_account, create_menu, create_meal, sample_image_file):
    student, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    images = client.get(f"/api/v1/me/meal-records/{record['id']}/images", headers=student["headers"]).json()["data"]
    image_file = Path(settings.UPLOAD_DIR) / "before"
    stored_file = next(image_file.glob("*"))
    stored_file.unlink()
    response = client.get(images[0]["image_url"], headers=student["headers"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IMAGE_FILE_NOT_FOUND"


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


def test_image_reupload_invalidates_previous_analysis(client, create_account, create_menu, create_meal, sample_image_file, sample_png_file, db_session_factory):
    student, meal, _ = _prepare_flow(client, create_account, create_menu, create_meal)
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    analyze = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert analyze.status_code == 200

    session = db_session_factory()
    try:
        stored_record = session.get(MealRecord, record["id"])
        old_before = next(image for image in stored_record.images if image.image_type == "BEFORE")
        old_before_file = Path(settings.UPLOAD_DIR) / old_before.image_url
        assert session.query(MealItemRecord).filter(MealItemRecord.meal_record_id == record["id"]).count() > 0
    finally:
        session.close()

    replace = client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_png_file})
    assert replace.status_code == 201

    session = db_session_factory()
    try:
        stored_record = session.get(MealRecord, record["id"])
        assert stored_record.status == "IMAGES_UPLOADED"
        assert stored_record.completed_at is None
        assert stored_record.failure_reason is None
        assert session.query(MealItemRecord).filter(MealItemRecord.meal_record_id == record["id"]).count() == 0
    finally:
        session.close()
    assert not old_before_file.exists()


def test_device_meal_record_rejects_yesterday_and_other_school(client, create_account, create_menu, create_meal):
    student, _, admin = _prepare_flow(client, create_account, create_menu, create_meal)
    yesterday_menu = create_menu(admin["headers"], name="어제메뉴")
    yesterday_meal = create_meal(admin["headers"], [yesterday_menu["id"]], meal_date=(today_local() - timedelta(days=1)).isoformat())
    response = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": yesterday_meal["id"]})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MEAL_DATE"

    other_school_menu = create_menu(admin["headers"], name="타학교메뉴")
    other_school_meal = create_meal(admin["headers"], [other_school_menu["id"]], school_name="다른학교")
    response = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": other_school_meal["id"]})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"
