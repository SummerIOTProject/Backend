from __future__ import annotations

import pytest

from app.core.exceptions import AppException
from app.models.meal_image import MealImage
from app.models.meal_item_record import MealItemRecord
from app.models.meal_record import MealRecord
from app.schemas.meal_analysis import VisionImageComparisonResultSchema
from app.services.vision.base import OpenAIVisionError
from app.utils.enums import AnalysisType


class DummyCompareProvider:
    analysis_type = AnalysisType.OPENAI_VLM

    def __init__(self, *, result=None, error=None):
        self.result = result or VisionImageComparisonResultSchema(
            same_meal=True,
            overall_consumed_ratio=0.72,
            confidence=0.81,
            items=[
                {
                    "item_name": "밥",
                    "consumed_ratio": 0.85,
                    "confidence": 0.88,
                    "before_description": "급식판 밥 칸 대부분이 채워져 있습니다.",
                    "after_description": "밥이 소량 남아 있습니다.",
                    "note": "대부분 섭취한 것으로 보입니다.",
                },
                {
                    "item_name": "육류 반찬",
                    "consumed_ratio": 0.65,
                    "confidence": 0.74,
                    "before_description": "육류 반찬이 한 칸에 제공되어 있습니다.",
                    "after_description": "일부 반찬이 남아 있습니다.",
                    "note": "약 65% 섭취한 것으로 추정됩니다.",
                },
            ],
            summary="밥은 대부분 섭취했고 일부 반찬이 남았습니다.",
            warnings=["식전과 식후 사진의 촬영 각도가 다릅니다."],
            analysis_possible=True,
            analysis_impossible_reason=None,
        )
        self.error = error

    async def compare_images(self, **kwargs):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture()
def compare_headers(create_account):
    account = create_account(login_id="compare-user", student_number="20229999")
    return account["headers"]


@pytest.fixture()
def compare_provider(monkeypatch):
    provider = DummyCompareProvider()
    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: provider)
    return provider


def _post_compare_images(client, *, headers, before_file=None, after_file=None):
    files = {}
    if before_file is not None:
        files["before_image"] = before_file
    if after_file is not None:
        files["after_image"] = after_file
    return client.post("/api/v1/analyses/compare-images", headers=headers, files=files)


def test_compare_images_upload_success(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["same_meal"] is True
    assert body["overall_consumed_ratio"] == 0.72
    assert len(body["items"]) == 2


def test_compare_images_requires_authentication(client, sample_image_file):
    response = _post_compare_images(client, headers={}, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 401


def test_compare_images_succeeds_without_meal_record_id_or_meal_id(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_compare_images_succeeds_without_today_meal_and_rfid(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 200
    assert response.json()["data"]["confidence"] == 0.81


def test_compare_images_does_not_create_meal_or_analysis_records(client, compare_headers, compare_provider, sample_image_file, db_session_factory):
    session = db_session_factory()
    try:
        meal_record_count = session.query(MealRecord).count()
        meal_image_count = session.query(MealImage).count()
        item_record_count = session.query(MealItemRecord).count()
    finally:
        session.close()

    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 200

    session = db_session_factory()
    try:
        assert session.query(MealRecord).count() == meal_record_count == 0
        assert session.query(MealImage).count() == meal_image_count == 0
        assert session.query(MealItemRecord).count() == item_record_count == 0
    finally:
        session.close()


def test_compare_images_requires_before_image(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, after_file=sample_image_file)
    assert response.status_code == 422


def test_compare_images_requires_after_image(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file)
    assert response.status_code == 422


def test_compare_images_rejects_empty_file(client, compare_headers, compare_provider):
    response = _post_compare_images(
        client,
        headers=compare_headers,
        before_file=("before.jpg", b"", "image/jpeg"),
        after_file=("after.jpg", b"", "image/jpeg"),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_IMAGE_FILE"


def test_compare_images_rejects_unsupported_content_type(client, compare_headers, compare_provider):
    response = _post_compare_images(
        client,
        headers=compare_headers,
        before_file=("before.txt", b"abc", "text/plain"),
        after_file=("after.txt", b"abc", "text/plain"),
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_IMAGE_FORMAT"


def test_compare_images_rejects_corrupted_image(client, compare_headers, compare_provider):
    response = _post_compare_images(
        client,
        headers=compare_headers,
        before_file=("before.jpg", b"not-an-image", "image/jpeg"),
        after_file=("after.jpg", b"not-an-image", "image/jpeg"),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE_DECODE"


def test_compare_images_rejects_oversized_file(client, compare_headers, compare_provider, sample_image_file, monkeypatch):
    monkeypatch.setattr("app.services.image_comparison_service.settings.MAX_ANALYSIS_IMAGE_SIZE_MB", 0)
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_compare_images_rejects_request_with_large_content_length(client, compare_headers, compare_provider, sample_image_file, monkeypatch):
    monkeypatch.setattr("app.services.image_comparison_service.settings.MAX_ANALYSIS_IMAGE_SIZE_MB", 1)
    response = client.post(
        "/api/v1/analyses/compare-images",
        headers={**compare_headers, "Content-Length": str((2 * 1024 * 1024) + 70000)},
        files={"before_image": sample_image_file, "after_image": sample_image_file},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_compare_images_parses_normal_vlm_json(client, compare_headers, compare_provider, sample_image_file):
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    data = response.json()["data"]
    assert response.status_code == 200
    assert data["items"][0]["before_description"] is not None
    assert data["items"][0]["after_description"] is not None


def test_compare_images_invalid_vlm_response_returns_502(client, compare_headers, sample_image_file, monkeypatch):
    class InvalidVLMResponse(AppException):
        def __init__(self):
            super().__init__(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="bad json")

    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: DummyCompareProvider(error=InvalidVLMResponse()))
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "VLM_INVALID_RESPONSE"


def test_compare_images_timeout_returns_504(client, compare_headers, sample_image_file, monkeypatch):
    timeout_error = OpenAIVisionError(message="VLM 요청 시간이 초과되었습니다.", code="VISION_TIMEOUT", status_code=503, detail="timeout")
    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: DummyCompareProvider(error=timeout_error))
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "VISION_TIMEOUT"


def test_compare_images_api_key_missing_returns_500(client, compare_headers, sample_image_file, monkeypatch):
    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: (_ for _ in ()).throw(OpenAIVisionError(message="VLM API 키가 설정되지 않았습니다.", code="VLM_API_KEY_NOT_CONFIGURED", status_code=500, detail="OPENAI_API_KEY missing")))
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "VLM_API_KEY_NOT_CONFIGURED"


def test_compare_images_same_meal_false_but_analysis_possible_returns_warning(client, compare_headers, sample_image_file, monkeypatch):
    uncertain = VisionImageComparisonResultSchema(
        same_meal=False,
        overall_consumed_ratio=0.41,
        confidence=0.33,
        items=[
            {
                "item_name": "알 수 없는 반찬",
                "consumed_ratio": 0.41,
                "confidence": 0.33,
                "before_description": "반찬 한 칸이 채워져 있습니다.",
                "after_description": "일부 음식이 남아 있습니다.",
                "note": "사진 각도 차이로 불확실합니다.",
            }
        ],
        summary="같은 식사일 가능성은 낮지만 제한적으로 비교했습니다.",
        warnings=["식전과 식후 사진의 급식판 구성이 완전히 일치하지 않습니다."],
        analysis_possible=True,
        analysis_impossible_reason=None,
    )
    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: DummyCompareProvider(result=uncertain))
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 200
    assert response.json()["data"]["same_meal"] is False


def test_compare_images_impossible_comparison_returns_400(client, compare_headers, sample_image_file, monkeypatch):
    impossible = VisionImageComparisonResultSchema(
        same_meal=False,
        overall_consumed_ratio=0.0,
        confidence=0.1,
        items=[
            {
                "item_name": "알 수 없는 반찬",
                "consumed_ratio": 0.0,
                "confidence": 0.1,
                "before_description": "구성이 불명확합니다.",
                "after_description": "비교할 수 없습니다.",
                "note": "비교 불가",
            }
        ],
        summary="두 이미지를 비교할 수 없습니다.",
        warnings=["서로 다른 식사로 보입니다."],
        analysis_possible=False,
        analysis_impossible_reason="same tray mismatch",
    )
    monkeypatch.setattr("app.services.image_comparison_service.build_compare_vision_provider", lambda: DummyCompareProvider(result=impossible))
    response = _post_compare_images(client, headers=compare_headers, before_file=sample_image_file, after_file=sample_image_file)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMAGES_NOT_COMPARABLE"
