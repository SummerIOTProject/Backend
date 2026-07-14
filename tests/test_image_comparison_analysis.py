from __future__ import annotations

from app.models.meal_record import MealRecord
from app.schemas.meal_analysis import VisionImageComparisonResultSchema
from app.utils.enums import AnalysisType


class DummyCompareProvider:
    def __init__(self, *, result=None, error=None):
        self.analysis_type = AnalysisType.OPENAI_VLM
        self.result = result or VisionImageComparisonResultSchema(
            overall_consumed_ratio=0.72,
            confidence=0.81,
            items=[
                {"item_name": "밥", "consumed_ratio": 0.85, "confidence": 0.88, "note": "소량만 남아 있습니다."},
                {"item_name": "육류 반찬", "consumed_ratio": 0.65, "confidence": 0.74, "note": "일부가 남아 있습니다."},
            ],
            summary="밥은 대부분 섭취했고 일부 반찬이 남았습니다.",
            warnings=["사진 촬영 각도가 달라 정확도가 낮아질 수 있습니다."],
            analysis_possible=True,
            same_meal=True,
            analysis_impossible_reason=None,
        )
        self.error = error

    async def compare_images(self, **kwargs):
        if self.error:
            raise self.error
        return self.result


def _make_auth_headers(create_account):
    account = create_account(login_id="compare-user", student_number="20229999")
    return account["headers"]


def _post_compare_images(client, *, before_file, after_file, headers=None):
    return client.post(
        "/api/v1/analyses/compare-images",
        headers=headers or {},
        files={"before_image": before_file, "after_image": after_file},
    )


def test_compare_images_upload_success(client, create_account, sample_image_file):
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["overall_consumed_ratio"] == 0.72
    assert len(body["items"]) == 2


def test_compare_images_requires_authentication(client, sample_image_file):
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 401


def test_compare_images_succeeds_without_meal_record_id_or_meal_id(client, create_account, sample_image_file):
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_compare_images_succeeds_without_today_meal_and_rfid(client, create_account, sample_image_file):
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 200
    assert response.json()["data"]["confidence"] == 0.81


def test_compare_images_does_not_create_meal_record(client, create_account, sample_image_file, db_session_factory):
    session = db_session_factory()
    try:
        before_count = session.query(MealRecord).count()
    finally:
        session.close()

    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 200

    session = db_session_factory()
    try:
        after_count = session.query(MealRecord).count()
        assert before_count == 0
        assert after_count == 0
    finally:
        session.close()


def test_compare_images_requires_before_image(client, create_account, sample_image_file):
    response = client.post("/api/v1/analyses/compare-images", headers=_make_auth_headers(create_account), files={"after_image": sample_image_file})
    assert response.status_code == 422


def test_compare_images_requires_after_image(client, create_account, sample_image_file):
    response = client.post("/api/v1/analyses/compare-images", headers=_make_auth_headers(create_account), files={"before_image": sample_image_file})
    assert response.status_code == 422


def test_compare_images_rejects_unsupported_content_type(client, create_account):
    response = client.post(
        "/api/v1/analyses/compare-images",
        headers=_make_auth_headers(create_account),
        files={
            "before_image": ("before.txt", b"abc", "text/plain"),
            "after_image": ("after.txt", b"abc", "text/plain"),
        },
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_IMAGE_FORMAT"


def test_compare_images_rejects_empty_file(client, create_account):
    response = client.post(
        "/api/v1/analyses/compare-images",
        headers=_make_auth_headers(create_account),
        files={
            "before_image": ("before.jpg", b"", "image/jpeg"),
            "after_image": ("after.jpg", b"", "image/jpeg"),
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_IMAGE_FILE"


def test_compare_images_rejects_oversized_file(client, create_account, sample_image_file, monkeypatch):
    monkeypatch.setattr("app.utils.files.settings.MAX_IMAGE_SIZE_MB", 0)
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_compare_images_rejects_request_with_large_content_length(client, create_account, sample_image_file, monkeypatch):
    monkeypatch.setattr("app.services.image_comparison_service.settings.MAX_IMAGE_SIZE_MB", 1)
    response = client.post(
        "/api/v1/analyses/compare-images",
        headers={**_make_auth_headers(create_account), "Content-Length": str((2 * 1024 * 1024) + 70000)},
        files={"before_image": sample_image_file, "after_image": sample_image_file},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_compare_images_mock_response_shape(client, create_account, sample_image_file):
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    data = response.json()["data"]
    assert response.status_code == 200
    assert 0.0 <= data["overall_consumed_ratio"] <= 1.0
    assert 0.0 <= data["confidence"] <= 1.0
    assert all(0.0 <= item["consumed_ratio"] <= 1.0 for item in data["items"])
    assert all(0.0 <= item["confidence"] <= 1.0 for item in data["items"])


def test_compare_images_invalid_vlm_response_returns_502(client, create_account, sample_image_file, monkeypatch):
    from app.core.exceptions import AppException

    class InvalidVLMResponse(AppException):
        def __init__(self):
            super().__init__(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="bad json")

    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyCompareProvider(error=InvalidVLMResponse()))
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "INVALID_VLM_RESPONSE"


def test_compare_images_impossible_comparison_returns_400(client, create_account, sample_image_file, monkeypatch):
    impossible = VisionImageComparisonResultSchema(
        overall_consumed_ratio=0.0,
        confidence=0.1,
        items=[{"item_name": "알 수 없는 반찬", "consumed_ratio": 0.0, "confidence": 0.1, "note": "비교 불가"}],
        summary="두 이미지를 비교할 수 없습니다.",
        warnings=["서로 다른 식사로 보입니다."],
        analysis_possible=False,
        same_meal=False,
        analysis_impossible_reason="same tray mismatch",
    )
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyCompareProvider(result=impossible))
    response = _post_compare_images(client, before_file=sample_image_file, after_file=sample_image_file, headers=_make_auth_headers(create_account))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMAGES_NOT_COMPARABLE"
