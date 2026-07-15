from types import SimpleNamespace
import asyncio

import pytest

from app.schemas.meal_analysis import VisionAnalysisResultSchema, VisionImageComparisonResultSchema
from app.services.vision.base import GeminiVisionError, OpenAIVisionError, VisionMenuInput, VisionProviderError
from app.services.vision.factory import build_compare_vision_provider, build_vision_provider
from app.services.vision.gemini_provider import GeminiVisionProvider
from app.services.vision.mock_provider import MockVisionProvider
from app.services.vision.openai_provider import OpenAIVisionProvider
from app.utils.enums import AnalysisType


class FakeGeminiAPIError(Exception):
    def __init__(self, code=None, message: str = "Gemini error", *, status_code=None):
        super().__init__(message)
        self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.message = message


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


class DummyProvider:
    def __init__(self, analysis_type=AnalysisType.OPENAI_VLM, result=None, error=None, capture=None):
        self.analysis_type = analysis_type
        self.result = result or VisionAnalysisResultSchema(
            items=[
                {"meal_menu_item_id": 1, "menu_id": 1, "menu_name": "wrong", "consumed_ratio": 0.8, "confidence": 0.9, "note": "ok"},
                {"meal_menu_item_id": 2, "menu_id": 2, "menu_name": "wrong2", "consumed_ratio": 0.2, "confidence": 0.8, "note": "ok"},
            ],
            analysis_note="provider result",
        )
        self.error = error
        self.capture = capture

    async def analyze(self, **kwargs):
        if self.capture is not None:
            self.capture.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def test_mock_analysis_success(client, create_account, create_menu, create_meal, sample_image_file):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 2
    assert response.json()["data"]["analysis_type"] == "MOCK"
    for item in response.json()["data"]["items"]:
        assert 0.85 <= item["consumed_ratio"] <= 0.94
        assert item["consumption_level"] == "MOST"


def test_provider_factory_selects_modes(monkeypatch):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = "MOCK"
    assert isinstance(build_vision_provider(), MockVisionProvider)

    settings.VISION_ANALYSIS_MODE = "GEMINI_VLM"
    settings.GEMINI_API_KEY = "gemini-key"
    settings.GEMINI_MODEL = "gemini-model"
    monkeypatch.setattr(GeminiVisionProvider, "_create_client", staticmethod(lambda: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace()))))
    assert isinstance(build_vision_provider(), GeminiVisionProvider)

    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_MODEL = "openai-model"
    monkeypatch.setattr(OpenAIVisionProvider, "_create_client", staticmethod(lambda: SimpleNamespace(responses=SimpleNamespace())))
    assert isinstance(build_vision_provider(), OpenAIVisionProvider)


def test_compare_provider_factory_requires_openai_api_key(monkeypatch):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    settings.OPENAI_API_KEY = None
    settings.OPENAI_VISION_MODEL = "gpt-4.1-mini"
    with pytest.raises(OpenAIVisionError) as exc_info:
        build_compare_vision_provider()
    assert exc_info.value.code == "VLM_API_KEY_NOT_CONFIGURED"


def test_compare_provider_factory_uses_openai_vision_model(monkeypatch):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = "OPENAI_VLM"
    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_VISION_MODEL = "gpt-4.1-mini"
    monkeypatch.setattr(OpenAIVisionProvider, "_create_client", lambda self: SimpleNamespace(responses=SimpleNamespace()))
    provider = build_compare_vision_provider()
    assert isinstance(provider, OpenAIVisionProvider)
    assert provider.model_name == "gpt-4.1-mini"


def test_compare_provider_factory_uses_gemini_without_openai_credentials(monkeypatch):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = "GEMINI_VLM"
    settings.GEMINI_API_KEY = "gemini-key"
    settings.GEMINI_MODEL = "gemini-2.5-flash"
    settings.OPENAI_API_KEY = None
    settings.OPENAI_MODEL = None
    settings.OPENAI_VISION_MODEL = None
    monkeypatch.setattr(GeminiVisionProvider, "_create_client", staticmethod(lambda: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace()))))

    provider = build_compare_vision_provider()

    assert isinstance(provider, GeminiVisionProvider)
    assert provider.model_name == "gemini-2.5-flash"


@pytest.mark.parametrize(
    ("api_key", "model", "expected_code"),
    [
        (None, "gemini-2.5-flash", "VLM_API_KEY_NOT_CONFIGURED"),
        ("gemini-key", None, "VLM_MODEL_NOT_CONFIGURED"),
    ],
)
def test_compare_provider_factory_validates_only_gemini_credentials(api_key, model, expected_code):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = "GEMINI_VLM"
    settings.GEMINI_API_KEY = api_key
    settings.GEMINI_MODEL = model
    settings.OPENAI_API_KEY = None
    with pytest.raises(VisionProviderError) as exc_info:
        build_compare_vision_provider()
    assert exc_info.value.code == expected_code


@pytest.mark.parametrize("mode", ["MOCK", "UNKNOWN_VLM"])
def test_compare_provider_factory_rejects_non_vlm_and_unknown_modes(mode):
    from app.core.config import settings

    settings.VISION_ANALYSIS_MODE = mode
    with pytest.raises(VisionProviderError) as exc_info:
        build_compare_vision_provider()
    assert exc_info.value.code == "VLM_MODE_NOT_SUPPORTED"


def test_openai_analysis_integration_uses_db_menu_names(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyProvider(analysis_type=AnalysisType.OPENAI_VLM))
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 200
    assert response.json()["data"]["analysis_type"] == "OPENAI_VLM"
    assert response.json()["data"]["items"][0]["menu_name"] == "제육볶음"


def test_gemini_analysis_integration_saves_analysis_type(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch, db_session_factory):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyProvider(analysis_type=AnalysisType.GEMINI_VLM))
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 200
    session = db_session_factory()
    try:
        from app.models.meal_item_record import MealItemRecord

        items = session.query(MealItemRecord).filter(MealItemRecord.meal_record_id == record["id"]).all()
        assert all(item.analysis_type == "GEMINI_VLM" for item in items)
    finally:
        session.close()


def test_analysis_reads_bytes_from_storage_backend(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    captured = []

    class FakeStorage:
        def read(self, key: str) -> bytes:
            return f"bytes:{key}".encode()

    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr("app.services.analysis_service.build_image_storage", lambda: FakeStorage())
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyProvider(analysis_type=AnalysisType.MOCK, capture=captured))
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 200
    assert captured[0]["before_image"].startswith(b"bytes:")
    assert captured[0]["after_image"].startswith(b"bytes:")
    assert captured[0]["before_mime_type"] == "image/jpeg"


def test_gemini_provider_receives_two_images_and_mime(monkeypatch):
    captured = []
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.model_name = "gemini-model"
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()

    async def fake_generate_content(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.75,"confidence":0.82,"note":"대부분 섭취됨"}],"analysis_note":"식전·식후 이미지 비교 결과"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/png",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )
    assert result.items[0].consumed_ratio == 0.75
    assert captured[0]["before_mime_type"] == "image/png"
    assert captured[0]["after_mime_type"] == "image/webp"


def test_invalid_json_response_fail(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    provider = DummyProvider(error=OpenAIVisionError(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", status_code=400, detail="invalid structured response"))
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: provider)
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_VLM_RESPONSE"


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (VisionAnalysisResultSchema(items=[{"meal_menu_item_id": 1, "menu_id": 1, "menu_name": "a", "consumed_ratio": 0.8, "confidence": 0.9, "note": "ok"}], analysis_note="x"), "VLM_MENU_MISSING"),
        (VisionAnalysisResultSchema(items=[{"meal_menu_item_id": 1, "menu_id": 1, "menu_name": "a", "consumed_ratio": 0.8, "confidence": 0.9, "note": "ok"}, {"meal_menu_item_id": 1, "menu_id": 1, "menu_name": "a", "consumed_ratio": 0.7, "confidence": 0.8, "note": "dup"}], analysis_note="x"), "VLM_DUPLICATE_MENU"),
        (VisionAnalysisResultSchema(items=[{"meal_menu_item_id": 1, "menu_id": 999, "menu_name": "a", "consumed_ratio": 0.8, "confidence": 0.9, "note": "ok"}, {"meal_menu_item_id": 2, "menu_id": 2, "menu_name": "b", "consumed_ratio": 0.2, "confidence": 0.8, "note": "ok"}], analysis_note="x"), "INVALID_VLM_RESPONSE"),
    ],
)
def test_result_validation_failures(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch, result, code):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr("app.services.vision_service.build_vision_provider", lambda: DummyProvider(result=result))
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_failure_sets_failed_status_and_no_mock_fallback(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch, db_session_factory):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr(
        "app.services.vision_service.build_vision_provider",
        lambda: DummyProvider(error=GeminiVisionError(message="VLM 요청 한도를 초과했습니다.", code="VISION_QUOTA_EXCEEDED", status_code=503, detail="gemini quota exceeded")),
    )
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VISION_QUOTA_EXCEEDED"
    session = db_session_factory()
    try:
        from app.models.meal_record import MealRecord

        stored = session.get(MealRecord, record["id"])
        assert stored.status == "FAILED"
        assert stored.failure_reason is not None
    finally:
        session.close()


def test_openai_provider_retries_server_errors(monkeypatch):
    from app.core.config import settings

    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_MODEL = "openai-model"
    provider = OpenAIVisionProvider.__new__(OpenAIVisionProvider)
    provider.provider_name = "openai"
    provider.analysis_type = AnalysisType.OPENAI_VLM
    provider.model_name = "openai-model"

    class DummyAPIStatusError(Exception):
        def __init__(self, status_code):
            self.status_code = status_code

    class DummyResponses:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise DummyAPIStatusError(500 if self.calls == 1 else 503)
            return SimpleNamespace(output_text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.75,"confidence":0.82,"note":"대부분 섭취됨"}],"analysis_note":"ok"}')

    provider.client = SimpleNamespace(responses=DummyResponses())
    import app.services.vision.openai_provider as module

    monkeypatch.setattr(module, "retry_with_backoff", module.retry_with_backoff)
    monkeypatch.setattr(module.OpenAIVisionProvider, "_should_retry", staticmethod(lambda exc: getattr(exc, "status_code", None) in {500, 503}))
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/png",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )
    assert result.items[0].consumed_ratio == 0.75


def test_openai_provider_bad_request_not_retried():
    from app.core.config import settings

    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_MODEL = "openai-model"
    provider = OpenAIVisionProvider.__new__(OpenAIVisionProvider)
    provider.provider_name = "openai"
    provider.analysis_type = AnalysisType.OPENAI_VLM
    provider.model_name = "openai-model"

    class DummyBadRequestError(Exception):
        pass

    class DummyResponses:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            raise DummyBadRequestError()

    provider.client = SimpleNamespace(responses=DummyResponses())
    provider._map_error = lambda exc: OpenAIVisionError(message="VLM 요청 형식이 올바르지 않습니다.", code="VISION_REQUEST_INVALID", status_code=400, detail="openai bad request")
    with pytest.raises(OpenAIVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/png",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
        )
    assert exc_info.value.code == "VISION_REQUEST_INVALID"
    assert provider.client.responses.calls == 1


def test_gemini_provider_parses_structured_response(monkeypatch):
    from app.core.config import settings

    settings.GEMINI_API_KEY = "gemini-key"
    settings.GEMINI_MODEL = "gemini-model"
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()

    async def fake_generate_content(**kwargs):
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취"}],"analysis_note":"식전·식후 이미지 비교 결과"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )
    assert result.items[0].confidence == 0.7
    assert result.analysis_note == "식전·식후 이미지 비교 결과"


def test_openai_compare_images_parses_structured_response():
    from app.core.config import settings

    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_MODEL = "openai-model"
    provider = OpenAIVisionProvider.__new__(OpenAIVisionProvider)
    provider.provider_name = "openai"
    provider.analysis_type = AnalysisType.OPENAI_VLM
    provider.model_name = "openai-model"

    class DummyResponses:
        async def create(self, **kwargs):
            return SimpleNamespace(
                output_text='{"overall_consumed_ratio":0.72,"confidence":0.81,"items":[{"item_name":"밥","consumed_ratio":0.85,"confidence":0.88,"note":"소량만 남아 있습니다."}],"summary":"밥은 대부분 섭취했습니다.","warnings":["사진 촬영 각도가 달라 정확도가 낮아질 수 있습니다."],"analysis_possible":true,"same_meal":true,"analysis_impossible_reason":null}'
            )

    provider.client = SimpleNamespace(responses=DummyResponses())
    result = asyncio.run(
        provider.compare_images(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/png",
        )
    )
    assert isinstance(result, VisionImageComparisonResultSchema)
    assert result.items[0].item_name == "밥"
    assert result.overall_consumed_ratio == 0.72


def test_openai_compare_images_retries_once_for_invalid_json():
    from app.core.config import settings

    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_VISION_MODEL = "gpt-4.1-mini"
    provider = OpenAIVisionProvider.__new__(OpenAIVisionProvider)
    provider.provider_name = "openai"
    provider.analysis_type = AnalysisType.OPENAI_VLM
    provider.model_name = "gpt-4.1-mini"

    class DummyResponses:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(output_text='{"bad_json":')
            return SimpleNamespace(
                output_text='{"same_meal":true,"overall_consumed_ratio":0.72,"confidence":0.81,"items":[{"item_name":"밥","consumed_ratio":0.85,"confidence":0.88,"before_description":"가득 담겨 있습니다.","after_description":"소량 남아 있습니다.","note":"대부분 섭취했습니다."}],"summary":"밥은 대부분 섭취했습니다.","warnings":[],"analysis_possible":true,"analysis_impossible_reason":null}'
            )

    provider.client = SimpleNamespace(responses=DummyResponses())
    result = asyncio.run(
        provider.compare_images(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/png",
        )
    )
    assert result.same_meal is True
    assert provider.client.responses.calls == 2


def test_openai_compare_images_invalid_json_after_retry_fails():
    from app.core.config import settings

    settings.OPENAI_API_KEY = "openai-key"
    settings.OPENAI_VISION_MODEL = "gpt-4.1-mini"
    provider = OpenAIVisionProvider.__new__(OpenAIVisionProvider)
    provider.provider_name = "openai"
    provider.analysis_type = AnalysisType.OPENAI_VLM
    provider.model_name = "gpt-4.1-mini"

    class DummyResponses:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(output_text='{"bad_json":')

    provider.client = SimpleNamespace(responses=DummyResponses())
    with pytest.raises(OpenAIVisionError) as exc_info:
        asyncio.run(
            provider.compare_images(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/png",
            )
        )
    assert exc_info.value.code == "INVALID_VLM_RESPONSE"
    assert provider.client.responses.calls == 2


def test_gemini_compare_images_parses_structured_response(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()

    async def fake_generate_content(**kwargs):
        return SimpleNamespace(
            text='{"overall_consumed_ratio":0.64,"confidence":0.77,"items":[{"item_name":"육류 반찬","consumed_ratio":0.60,"confidence":0.70,"note":"절반 이상 섭취"}],"summary":"주요 반찬을 절반 이상 섭취했습니다.","warnings":[],"analysis_possible":true,"same_meal":true,"analysis_impossible_reason":null}'
        )

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.compare_images(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
        )
    )
    assert isinstance(result, VisionImageComparisonResultSchema)
    assert result.summary == "주요 반찬을 절반 이상 섭취했습니다."


def test_gemini_compare_images_sends_before_after_then_instruction():
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.model_name = "gemini-2.5-flash"
    captured = {}

    class DummyModels:
        async def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="{}")

    provider.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModels()))
    asyncio.run(
        provider._generate_content(
            before_image=b"before-bytes",
            before_mime_type="image/jpeg",
            after_image=b"after-bytes",
            after_mime_type="image/webp",
            prompt_text="comparison instruction",
            schema={"type": "object"},
        )
    )

    parts = captured["contents"][0].parts
    assert parts[0].inline_data.data == b"before-bytes"
    assert parts[0].inline_data.mime_type == "image/jpeg"
    assert parts[1].inline_data.data == b"after-bytes"
    assert parts[1].inline_data.mime_type == "image/webp"
    assert parts[2].text == "comparison instruction"
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].response_json_schema == {"type": "object"}


@pytest.mark.parametrize("status_code", [500, 502, 503, 504, 429])
def test_gemini_provider_retries_retryable_status_codes(monkeypatch, status_code):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()

    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise FakeGeminiAPIError(status_code, "quota exceeded" if status_code == 429 else "provider unavailable")
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취"}],"analysis_note":"ok"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )
    assert calls["count"] == 2
    assert result.items[0].consumed_ratio == 0.6


def test_gemini_provider_invalid_extra_field_fails(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()

    async def fake_generate_content(**kwargs):
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취","extra":"x"}],"analysis_note":"ok"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    with pytest.raises(GeminiVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/webp",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
    )
    assert exc_info.value.code == "INVALID_VLM_RESPONSE"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (FakeGeminiAPIError(429), 429),
        (FakeGeminiAPIError("429", status_code=503), 503),
        (FakeGeminiAPIError("bad"), None),
        (Exception("plain"), None),
    ],
)
def test_gemini_status_code_extraction(exc, expected):
    assert GeminiVisionProvider._get_status_code(exc) == expected


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, "VISION_REQUEST_INVALID"),
        (401, "VISION_AUTHENTICATION_FAILED"),
        (403, "VISION_PERMISSION_DENIED"),
        (404, "VISION_REQUEST_INVALID"),
        (429, "VISION_QUOTA_EXCEEDED"),
        (500, "VISION_PROVIDER_UNAVAILABLE"),
        (502, "VISION_PROVIDER_UNAVAILABLE"),
        (503, "VISION_PROVIDER_UNAVAILABLE"),
        (504, "VISION_PROVIDER_UNAVAILABLE"),
    ],
)
def test_gemini_map_error_by_status_code(status_code, expected_code):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    error = provider._map_error(FakeGeminiAPIError(status_code))
    assert error.code == expected_code


@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_gemini_provider_does_not_retry_non_retryable_status_codes(monkeypatch, status_code):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        raise FakeGeminiAPIError(status_code)

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)

    with pytest.raises(GeminiVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/webp",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
        )

    assert calls["count"] == 1
    assert exc_info.value.code in {"VISION_REQUEST_INVALID", "VISION_AUTHENTICATION_FAILED", "VISION_PERMISSION_DENIED"}


def test_gemini_provider_retries_timeout_then_success(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise asyncio.TimeoutError()
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취"}],"analysis_note":"ok"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )

    assert calls["count"] == 2
    assert result.items[0].consumed_ratio == 0.6


def test_gemini_provider_retries_connection_error_then_success(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ConnectionError("connection lost")
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취"}],"analysis_note":"ok"}')

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)
    result = asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )

    assert calls["count"] == 2
    assert result.items[0].consumed_ratio == 0.6


def test_gemini_provider_timeout_setting_applies(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 7
    provider.client = SimpleNamespace()
    captured = {}

    async def fake_wait_for(awaitable, timeout):
        captured["timeout"] = timeout
        return await awaitable

    async def fake_generate_content(**kwargs):
        return SimpleNamespace(text='{"items":[{"meal_menu_item_id":1,"menu_id":10,"menu_name":"제육볶음","consumed_ratio":0.6,"confidence":0.7,"note":"절반 이상 섭취"}],"analysis_note":"ok"}')

    monkeypatch.setattr("app.services.vision.gemini_provider.asyncio.wait_for", fake_wait_for)
    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)

    asyncio.run(
        provider.analyze(
            before_image=b"before",
            before_mime_type="image/jpeg",
            after_image=b"after",
            after_mime_type="image/webp",
            menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
        )
    )

    assert captured["timeout"] == 7


def test_gemini_provider_timeout_final_failure(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        raise asyncio.TimeoutError()

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)

    with pytest.raises(GeminiVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/webp",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
        )

    assert exc_info.value.code == "VISION_TIMEOUT"
    assert calls["count"] == 3


def test_gemini_provider_provider_unavailable_after_max_retries(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        raise FakeGeminiAPIError(503)

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)

    with pytest.raises(GeminiVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/webp",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
        )

    assert exc_info.value.code == "VISION_PROVIDER_UNAVAILABLE"
    assert calls["count"] == 3


def test_gemini_provider_quota_exceeded_after_max_retries(monkeypatch):
    provider = GeminiVisionProvider.__new__(GeminiVisionProvider)
    provider.provider_name = "gemini"
    provider.analysis_type = AnalysisType.GEMINI_VLM
    provider.model_name = "gemini-model"
    provider.timeout_seconds = 3
    provider.client = SimpleNamespace()
    calls = {"count": 0}

    async def fake_sleep(_: float):
        return None

    monkeypatch.setattr("app.services.vision.base.asyncio.sleep", fake_sleep)

    async def fake_generate_content(**kwargs):
        calls["count"] += 1
        raise FakeGeminiAPIError(429, "quota exceeded")

    monkeypatch.setattr(provider, "_generate_content", fake_generate_content)

    with pytest.raises(GeminiVisionError) as exc_info:
        asyncio.run(
            provider.analyze(
                before_image=b"before",
                before_mime_type="image/jpeg",
                after_image=b"after",
                after_mime_type="image/webp",
                menu_items=[VisionMenuInput(meal_menu_item_id=1, menu_id=10, menu_name="제육볶음")],
            )
        )

    assert exc_info.value.code == "VISION_QUOTA_EXCEEDED"
    assert calls["count"] == 3


def test_failure_sets_failed_status_and_no_partial_items_saved(client, create_account, create_menu, create_meal, sample_image_file, monkeypatch, db_session_factory):
    student, _, record = _prepare_record_for_analysis(client, create_account, create_menu, create_meal, sample_image_file)
    monkeypatch.setattr(
        "app.services.vision_service.build_vision_provider",
        lambda: DummyProvider(error=GeminiVisionError(message="VLM 요청 시간이 초과되었습니다.", code="VISION_TIMEOUT", status_code=503, detail="request timed out")),
    )
    response = client.post(f"/api/v1/me/meal-records/{record['id']}/analyze", headers=student["headers"])
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VISION_TIMEOUT"
    session = db_session_factory()
    try:
        from app.models.meal_item_record import MealItemRecord
        from app.models.meal_record import MealRecord

        stored = session.get(MealRecord, record["id"])
        assert stored.status == "FAILED"
        assert stored.completed_at is None
        assert stored.failure_reason == "GeminiVisionError: request timed out"
        assert session.query(MealItemRecord).filter(MealItemRecord.meal_record_id == record["id"]).count() == 0
    finally:
        session.close()
