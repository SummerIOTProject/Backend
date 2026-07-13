from types import SimpleNamespace


def _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file):
    admin = create_account(login_id="admin1", student_number="90000001", role="ADMIN")
    student = create_account(login_id="student1", student_number="20223137")
    menu1 = create_menu(admin["headers"], name="제육볶음")
    menu2 = create_menu(admin["headers"], name="김치", allergen_codes=[])
    meal = create_meal(admin["headers"], [menu1["id"], menu2["id"]])
    client.post("/api/v1/me/rfid-cards", headers=student["headers"], json={"uid": "04A3B29C7F6180"})
    record = client.post("/api/v1/device/meal-records", headers={"X-Device-Key": "device-secret"}, json={"rfid_uid": "04A3B29C7F6180", "meal_id": meal["id"]}).json()["data"]
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/before", headers=student["headers"], files={"file": sample_image_file})
    client.post(f"/api/v1/me/meal-records/{record['id']}/images/after", headers=student["headers"], files={"file": sample_image_file})
    return student, meal, record


def _patch_openai(monkeypatch, output_text, *, error=None):
    class DummyResponses:
        async def create(self, **kwargs):
            if error:
                raise error
            return SimpleNamespace(output_text=output_text)

    from app.services.vision_service import VisionService

    monkeypatch.setattr(VisionService, "__init__", lambda self: setattr(self, "client", SimpleNamespace(responses=DummyResponses())))


def test_mock_analysis_success(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 2


def test_openai_client_mock_success(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.core.config import settings

    settings.OPENAI_API_KEY = "test-key"
    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    _patch_openai(monkeypatch, '{"items":[{"meal_menu_item_id":1,"menu_id":1,"menu_name":"wrong","consumed_ratio":0.8,"confidence":0.9,"note":"ok"},{"meal_menu_item_id":2,"menu_id":2,"menu_name":"wrong2","consumed_ratio":0.2,"confidence":0.8,"note":"ok"}]}')
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["menu_name"] == "제육볶음"


def test_invalid_json_response_fail(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.core.config import settings

    settings.OPENAI_API_KEY = "test-key"
    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    _patch_openai(monkeypatch, '{"items": [}')
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_VLM_RESPONSE"


def test_menu_missing_response_fail(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.core.config import settings

    settings.OPENAI_API_KEY = "test-key"
    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    _patch_openai(monkeypatch, '{"items":[{"meal_menu_item_id":1,"menu_id":1,"menu_name":"제육볶음","consumed_ratio":0.8,"confidence":0.9,"note":"ok"}]}')
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VLM_MENU_MISSING"


def test_duplicate_menu_response_fail(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.core.config import settings

    settings.OPENAI_API_KEY = "test-key"
    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    _patch_openai(monkeypatch, '{"items":[{"meal_menu_item_id":1,"menu_id":1,"menu_name":"제육볶음","consumed_ratio":0.8,"confidence":0.9,"note":"ok"},{"meal_menu_item_id":1,"menu_id":1,"menu_name":"제육볶음","consumed_ratio":0.7,"confidence":0.8,"note":"dup"}]}')
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VLM_DUPLICATE_MENU"


def test_wrong_menu_id_and_failed_status_saved(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch, db_session_factory):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.core.config import settings
    from app.models.meal_record import MealRecord

    settings.OPENAI_API_KEY = "test-key"
    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    _patch_openai(monkeypatch, '{"items":[{"meal_menu_item_id":1,"menu_id":999,"menu_name":"제육볶음","consumed_ratio":0.8,"confidence":0.9,"note":"ok"},{"meal_menu_item_id":2,"menu_id":2,"menu_name":"김치","consumed_ratio":0.2,"confidence":0.8,"note":"ok"}]}')
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert response.status_code == 400
    session = db_session_factory()
    try:
        stored = session.get(MealRecord, record["id"])
        assert stored.status == "FAILED"
        assert stored.failure_reason is not None
    finally:
        session.close()


def test_analysis_already_running_conflict(client, create_account, create_menu, create_meal, sample_image_file, db_session_factory):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    from app.models.meal_record import MealRecord

    session = db_session_factory()
    try:
        stored = session.get(MealRecord, record["id"])
        stored.status = "ANALYZING"
        session.commit()
    finally:
        session.close()
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ANALYSIS_ALREADY_RUNNING"
