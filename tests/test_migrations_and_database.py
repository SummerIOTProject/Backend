from pathlib import Path
from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Allergen,
    Meal,
    MealItemRecord,
    MealMenuItem,
    MealRecord,
    Menu,
    RFIDCard,
    User,
)


def test_alembic_upgrade_head_seeds_allergens(tmp_path, monkeypatch):
    db_path = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)

    config = Config(str(Path("alembic.ini").resolve()))
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"users", "allergens", "menus", "meal_records", "meal_item_records", "serving_recommendations"} <= tables

    with Session(engine) as session:
        codes = {code for (code,) in session.execute(text("SELECT code FROM allergens"))}
        assert len(codes) == 19
        assert {"EGGS", "SULFITES", "PINE_NUT"} <= codes
        assert "EGG" not in codes
        assert "SULFITE" not in codes


def test_sqlite_foreign_keys_and_constraints(db_session_factory):
    session = db_session_factory()
    try:
        pragma = session.execute(text("PRAGMA foreign_keys")).scalar()
        assert pragma == 1

        user = User(
            login_id="student1",
            hashed_password="hashed-password",
            name="학생",
            student_number="20223137",
            role="STUDENT",
            is_active=True,
        )
        session.add(user)
        session.flush()

        menu = Menu(
            name="제약메뉴",
            standard_serving_g=100,
            calories_per_100g=100,
            carbohydrate_per_100g=10,
            protein_per_100g=10,
            fat_per_100g=5,
            is_active=True,
        )
        session.add(menu)
        session.flush()

        meal = Meal(meal_date=date(2026, 7, 13), meal_type="LUNCH", school_name="국민대학교")
        session.add(meal)
        session.flush()

        meal_menu_item = MealMenuItem(meal_id=meal.id, menu_id=menu.id)
        session.add(meal_menu_item)
        session.flush()

        record = MealRecord(user_id=user.id, meal_id=meal.id, status="COMPLETED")
        session.add(record)
        session.flush()

        item = MealItemRecord(
            meal_record_id=record.id,
            meal_menu_item_id=meal_menu_item.id,
            consumed_ratio=0.5,
            consumption_level="HALF",
            confidence=0.9,
            analysis_type="MOCK",
        )
        session.add(item)

        card = RFIDCard(user_id=user.id, uid="04A3B29C7F6180", is_active=True)
        session.add(card)
        session.commit()

        session.delete(menu)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        user_id = user.id
        item_id = item.id
        session.delete(user)
        session.commit()
        assert session.get(RFIDCard, card.id) is None
        assert session.get(MealRecord, record.id) is None
        orphaned_item = session.get(MealItemRecord, item_id)
        assert orphaned_item is None
        assert session.get(User, user_id) is None
    finally:
        session.close()


def test_meal_item_record_corrected_by_set_null(db_session_factory):
    session = db_session_factory()
    try:
        user = User(
            login_id="student1",
            hashed_password="hashed-password",
            name="학생",
            student_number="20223137",
            role="STUDENT",
            is_active=True,
        )
        corrector = User(
            login_id="student2",
            hashed_password="hashed-password",
            name="보정자",
            student_number="20223138",
            role="STUDENT",
            is_active=True,
        )
        menu = Menu(
            name="SETNULL메뉴",
            standard_serving_g=100,
            calories_per_100g=100,
            carbohydrate_per_100g=10,
            protein_per_100g=10,
            fat_per_100g=5,
            is_active=True,
        )
        meal = Meal(meal_date=date(2026, 7, 13), meal_type="LUNCH", school_name="국민대학교")
        session.add_all([user, corrector, menu, meal])
        session.flush()
        meal_menu_item = MealMenuItem(meal_id=meal.id, menu_id=menu.id)
        session.add(meal_menu_item)
        session.flush()
        record = MealRecord(user_id=user.id, meal_id=meal.id, status="COMPLETED")
        session.add(record)
        session.flush()
        item = MealItemRecord(
            meal_record_id=record.id,
            meal_menu_item_id=meal_menu_item.id,
            consumed_ratio=0.5,
            consumption_level="HALF",
            confidence=0.9,
            analysis_type="MOCK",
            corrected_by=corrector.id,
            is_corrected=True,
        )
        session.add(item)
        session.commit()

        session.delete(corrector)
        session.commit()
        refreshed = session.get(MealItemRecord, item.id)
        assert refreshed is not None
        assert refreshed.corrected_by is None
    finally:
        session.close()
