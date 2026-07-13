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


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE allergens SET code = 'EGGS' WHERE code = 'EGG'"))
    bind.execute(sa.text("UPDATE allergens SET code = 'SULFITES' WHERE code = 'SULFITE'"))

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
    bind.execute(sa.text("UPDATE allergens SET code = 'EGG' WHERE code = 'EGGS'"))
    bind.execute(sa.text("UPDATE allergens SET code = 'SULFITE' WHERE code = 'SULFITES'"))
    bind.execute(sa.text("DELETE FROM allergens WHERE code = 'PINE_NUT'"))
