"""normalize allergen seed codes

Revision ID: 20260712_0002
Revises: 20260712_0001
Create Date: 2026-07-13 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0002"
down_revision = "20260712_0001"
branch_labels = None
depends_on = None

ALLERGENS = [
    ("EGGS", "난류", 1),
    ("MILK", "우유", 2),
    ("BUCKWHEAT", "메밀", 3),
    ("PEANUT", "땅콩", 4),
    ("SOYBEAN", "대두", 5),
    ("WHEAT", "밀", 6),
    ("MACKEREL", "고등어", 7),
    ("CRAB", "게", 8),
    ("SHRIMP", "새우", 9),
    ("PORK", "돼지고기", 10),
    ("PEACH", "복숭아", 11),
    ("TOMATO", "토마토", 12),
    ("SULFITES", "아황산류", 13),
    ("WALNUT", "호두", 14),
    ("CHICKEN", "닭고기", 15),
    ("BEEF", "쇠고기", 16),
    ("SQUID", "오징어", 17),
    ("SHELLFISH", "조개류", 18),
    ("PINE_NUT", "잣", 19),
]


def _get_allergen_id(bind, code: str) -> int | None:
    return bind.execute(sa.text("SELECT id FROM allergens WHERE code = :code"), {"code": code}).scalar()


def _merge_allergen_code(bind, old_code: str, new_code: str) -> None:
    old_id = _get_allergen_id(bind, old_code)
    new_id = _get_allergen_id(bind, new_code)
    if old_id is None:
        return
    if new_id is None:
        bind.execute(sa.text("UPDATE allergens SET code = :new_code WHERE id = :old_id"), {"new_code": new_code, "old_id": old_id})
        return
    if old_id == new_id:
        return

    bind.execute(
        sa.text(
            """
            UPDATE user_allergies
            SET allergen_id = :new_id
            WHERE allergen_id = :old_id
              AND NOT EXISTS (
                SELECT 1
                FROM user_allergies ua2
                WHERE ua2.user_id = user_allergies.user_id
                  AND ua2.allergen_id = :new_id
              )
            """
        ),
        {"old_id": old_id, "new_id": new_id},
    )
    bind.execute(sa.text("DELETE FROM user_allergies WHERE allergen_id = :old_id"), {"old_id": old_id})

    bind.execute(
        sa.text(
            """
            UPDATE menu_allergens
            SET allergen_id = :new_id
            WHERE allergen_id = :old_id
              AND NOT EXISTS (
                SELECT 1
                FROM menu_allergens ma2
                WHERE ma2.menu_id = menu_allergens.menu_id
                  AND ma2.allergen_id = :new_id
              )
            """
        ),
        {"old_id": old_id, "new_id": new_id},
    )
    bind.execute(sa.text("DELETE FROM menu_allergens WHERE allergen_id = :old_id"), {"old_id": old_id})
    bind.execute(sa.text("DELETE FROM allergens WHERE id = :old_id"), {"old_id": old_id})


def upgrade() -> None:
    bind = op.get_bind()
    _merge_allergen_code(bind, "EGG", "EGGS")
    _merge_allergen_code(bind, "SULFITE", "SULFITES")

    allergen_table = sa.table(
        "allergens",
        sa.column("code", sa.String()),
        sa.column("name_ko", sa.String()),
        sa.column("display_number", sa.Integer()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    existing_codes = {row[0] for row in bind.execute(sa.text("SELECT code FROM allergens"))}
    for code, name_ko, display_number in ALLERGENS:
        if code in existing_codes:
            bind.execute(
                sa.text(
                    "UPDATE allergens SET name_ko = :name_ko, display_number = :display_number, is_active = 1 WHERE code = :code"
                ),
                {"code": code, "name_ko": name_ko, "display_number": display_number},
            )
        else:
            op.bulk_insert(
                allergen_table,
                [{"code": code, "name_ko": name_ko, "display_number": display_number, "description": None, "is_active": True}],
            )


def downgrade() -> None:
    bind = op.get_bind()
    _merge_allergen_code(bind, "EGGS", "EGG")
    _merge_allergen_code(bind, "SULFITES", "SULFITE")
    bind.execute(sa.text("DELETE FROM allergens WHERE code = 'PINE_NUT'"))
