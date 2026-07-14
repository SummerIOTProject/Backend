import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.allergen_seed import ALLERGEN_SEEDS
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models import Allergen, Meal, MealItemRecord, MealMenuItem, MealRecord, Menu, User
from app.utils.datetime import today_local
from app.utils.enums import UserRole


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DEVICE_API_KEY", "device-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("STORAGE_BACKEND", "LOCAL")
    monkeypatch.setenv("VISION_ANALYSIS_MODE", "MOCK")
    monkeypatch.setenv("VISION_MAX_RETRIES", "2")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("SCHOOL_NAME", "국민대학교")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Seoul")
    settings.DEVICE_API_KEY = "device-secret"
    settings.JWT_SECRET_KEY = "test-secret"
    settings.UPLOAD_DIR = str(upload_dir)
    settings.STORAGE_BACKEND = "LOCAL"
    settings.VISION_ANALYSIS_MODE = "MOCK"
    settings.VISION_MAX_RETRIES = 2
    settings.OPENAI_API_KEY = None
    settings.OPENAI_MODEL = None
    settings.VISION_MODEL = None
    settings.GEMINI_API_KEY = None
    settings.GEMINI_MODEL = None
    settings.BLOB_STORE_ID = None
    settings.BLOB_READ_WRITE_TOKEN = None
    settings.VERCEL_OIDC_TOKEN = None
    settings.SCHOOL_NAME = "국민대학교"
    settings.APP_TIMEZONE = "Asia/Seoul"

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        for code, name_ko, display_number in ALLERGEN_SEEDS:
            session.add(Allergen(code=code, name_ko=name_ko, display_number=display_number, is_active=True))
        session.commit()
    finally:
        session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.testing_session_local = TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_image_file():
    def _make(fmt: str, filename: str, content_type: str, *, orientation: int | None = None):
        image = Image.new("RGB", (120, 80), color=(120, 40, 200))
        output = io.BytesIO()
        save_kwargs = {}
        if fmt == "JPEG" and orientation is not None:
            from PIL import TiffImagePlugin

            exif = Image.Exif()
            exif[274] = orientation
            save_kwargs["exif"] = exif
        image.save(output, format=fmt, **save_kwargs)
        output.seek(0)
        return (filename, output, content_type)

    return _make("JPEG", "sample.jpg", "image/jpeg")


@pytest.fixture()
def sample_png_file():
    image = Image.new("RGBA", (120, 80), color=(120, 40, 200, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return ("sample.png", output, "image/png")


@pytest.fixture()
def sample_webp_file():
    image = Image.new("RGB", (120, 80), color=(120, 40, 200))
    output = io.BytesIO()
    image.save(output, format="WEBP")
    output.seek(0)
    return ("sample.webp", output, "image/webp")


@pytest.fixture()
def exif_rotated_jpeg_file():
    image = Image.new("RGB", (120, 80), color=(120, 40, 200))
    output = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    image.save(output, format="JPEG", exif=exif)
    output.seek(0)
    return ("rotated.jpg", output, "image/jpeg")


@pytest.fixture()
def create_account(client):
    def _create_account(*, login_id: str, student_number: str, name: str = "학생", password: str = "Password123!", role: UserRole = UserRole.STUDENT, allergen_codes=None):
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "login_id": login_id,
                "password": password,
                "name": name,
                "student_number": student_number,
                "allergen_codes": allergen_codes or [],
            },
        )
        assert response.status_code == 201
        user_id = response.json()["data"]["id"]

        if role != UserRole.STUDENT:
            session = client.app.state.testing_session_local()
            try:
                user = session.get(User, user_id)
                user.role = role
                session.commit()
            finally:
                session.close()

        login_response = client.post("/api/v1/auth/login", json={"login_id": login_id, "password": password})
        assert login_response.status_code == 200
        tokens = login_response.json()["data"]
        return {
            "user_id": user_id,
            "login_id": login_id,
            "password": password,
            "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
            "refresh_token": tokens["refresh_token"],
        }

    return _create_account


@pytest.fixture()
def create_menu(client):
    def _create_menu(admin_headers, name="제육볶음", allergen_codes=None, standard_serving_g=120, nutrition=None):
        response = client.post(
            "/api/v1/admin/menus",
            headers=admin_headers,
            json={
                "name": name,
                "standard_serving_g": standard_serving_g,
                "nutrition_per_100g": nutrition or {
                    "calories_kcal": 220,
                    "carbohydrate_g": 12,
                    "protein_g": 18,
                    "fat_g": 11,
                },
                "ingredients": ["돼지고기", "양파", "고추장", "간장"],
                "allergen_codes": allergen_codes or ["SOYBEAN", "WHEAT"],
            },
        )
        assert response.status_code == 201
        return response.json()["data"]

    return _create_menu


@pytest.fixture()
def create_meal(client):
    def _create_meal(admin_headers, menu_ids, *, meal_date=None, meal_type="LUNCH", school_name="국민대학교"):
        response = client.post(
            "/api/v1/admin/meals",
            headers=admin_headers,
            json={
                "meal_date": meal_date or today_local().isoformat(),
                "meal_type": meal_type,
                "school_name": school_name,
                "menu_ids": menu_ids,
            },
        )
        assert response.status_code == 201
        return response.json()["data"]

    return _create_meal


@pytest.fixture()
def db_session_factory(client):
    return client.app.state.testing_session_local


@pytest.fixture()
def make_completed_record(db_session_factory):
    def _make(*, user_id: int, menu_id: int, days_ago: int, consumed_ratio: float, status="COMPLETED", meal_type="LUNCH", school_name="국민대학교"):
        session = db_session_factory()
        try:
            menu = session.get(Menu, menu_id)
            meal = Meal(meal_date=today_local() - timedelta(days=days_ago), meal_type=meal_type, school_name=school_name)
            session.add(meal)
            session.flush()
            meal_menu_item = MealMenuItem(meal_id=meal.id, menu_id=menu_id)
            session.add(meal_menu_item)
            session.flush()
            record = MealRecord(user_id=user_id, meal_id=meal.id, status=status)
            session.add(record)
            session.flush()
            if status == "COMPLETED":
                item = MealItemRecord(
                    meal_record_id=record.id,
                    meal_menu_item_id=meal_menu_item.id,
                    consumed_ratio=consumed_ratio,
                    consumption_level="HALF",
                    confidence=0.9,
                    analysis_type="MOCK",
                )
                session.add(item)
            session.commit()
            return record.id
        finally:
            session.close()

    return _make
