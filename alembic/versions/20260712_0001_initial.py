"""initial schema

Revision ID: 20260712_0001
Revises:
Create Date: 2026-07-12 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0001"
down_revision = None
branch_labels = None
depends_on = None

bigint_pk = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("student_number", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_student_number", "users", ["student_number"], unique=True)

    op.create_table(
        "meals",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=20), nullable=False),
        sa.Column("school_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meal_date", "meal_type", "school_name", name="uq_meal_date_type_school"),
    )
    op.create_index("ix_meals_meal_date", "meals", ["meal_date"], unique=False)
    op.create_index("ix_meals_meal_type", "meals", ["meal_type"], unique=False)

    op.create_table(
        "rfid_cards",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uid", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rfid_cards_uid", "rfid_cards", ["uid"], unique=True)
    op.create_index("ix_rfid_cards_user_id", "rfid_cards", ["user_id"], unique=False)

    op.create_table(
        "meal_menu_items",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_id", bigint_pk, sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("tray_section", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_meal_menu_items_meal_id", "meal_menu_items", ["meal_id"], unique=False)

    op.create_table(
        "meal_records",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_id", bigint_pk, sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("user_id", "meal_id", name="uq_meal_record_user_meal"),
    )
    op.create_index("ix_meal_records_user_id", "meal_records", ["user_id"], unique=False)
    op.create_index("ix_meal_records_meal_id", "meal_records", ["meal_id"], unique=False)

    op.create_table(
        "meal_images",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_record_id", bigint_pk, sa.ForeignKey("meal_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_type", sa.String(length=20), nullable=False),
        sa.Column("image_url", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meal_record_id", "image_type", name="uq_meal_image_record_type"),
    )
    op.create_index("ix_meal_images_meal_record_id", "meal_images", ["meal_record_id"], unique=False)

    op.create_table(
        "meal_analyses",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_record_id", bigint_pk, sa.ForeignKey("meal_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_menu_item_id", bigint_pk, sa.ForeignKey("meal_menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumed_ratio", sa.Float(), nullable=False),
        sa.Column("consumption_level", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meal_record_id", "meal_menu_item_id", name="uq_analysis_record_menu"),
    )
    op.create_index("ix_meal_analyses_meal_record_id", "meal_analyses", ["meal_record_id"], unique=False)
    op.create_index("ix_meal_analyses_meal_menu_item_id", "meal_analyses", ["meal_menu_item_id"], unique=False)

    op.create_table(
        "serving_recommendations",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_menu_item_id", bigint_pk, sa.ForeignKey("meal_menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_level", sa.String(length=20), nullable=False),
        sa.Column("average_consumed_ratio", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_serving_recommendations_user_id", "serving_recommendations", ["user_id"], unique=False)
    op.create_index(
        "ix_serving_recommendations_meal_menu_item_id",
        "serving_recommendations",
        ["meal_menu_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_serving_recommendations_meal_menu_item_id", table_name="serving_recommendations")
    op.drop_index("ix_serving_recommendations_user_id", table_name="serving_recommendations")
    op.drop_table("serving_recommendations")
    op.drop_index("ix_meal_analyses_meal_menu_item_id", table_name="meal_analyses")
    op.drop_index("ix_meal_analyses_meal_record_id", table_name="meal_analyses")
    op.drop_table("meal_analyses")
    op.drop_index("ix_meal_images_meal_record_id", table_name="meal_images")
    op.drop_table("meal_images")
    op.drop_index("ix_meal_records_meal_id", table_name="meal_records")
    op.drop_index("ix_meal_records_user_id", table_name="meal_records")
    op.drop_table("meal_records")
    op.drop_index("ix_meal_menu_items_meal_id", table_name="meal_menu_items")
    op.drop_table("meal_menu_items")
    op.drop_index("ix_rfid_cards_user_id", table_name="rfid_cards")
    op.drop_index("ix_rfid_cards_uid", table_name="rfid_cards")
    op.drop_table("rfid_cards")
    op.drop_index("ix_meals_meal_type", table_name="meals")
    op.drop_index("ix_meals_meal_date", table_name="meals")
    op.drop_table("meals")
    op.drop_index("ix_users_student_number", table_name="users")
    op.drop_table("users")
