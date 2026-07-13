"""initial normalized schema

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
        sa.Column("login_id", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("student_number", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="STUDENT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)
    op.create_index("ix_users_student_number", "users", ["student_number"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "allergens",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name_ko", sa.String(length=100), nullable=False),
        sa.Column("display_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_allergens_code", "allergens", ["code"], unique=True)

    op.create_table(
        "ingredients",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingredients_name", "ingredients", ["name"], unique=True)

    op.create_table(
        "menus",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("standard_serving_g", sa.Float(), nullable=False),
        sa.Column("calories_per_100g", sa.Float(), nullable=False),
        sa.Column("carbohydrate_per_100g", sa.Float(), nullable=False),
        sa.Column("protein_per_100g", sa.Float(), nullable=False),
        sa.Column("fat_per_100g", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("standard_serving_g > 0", name="ck_menus_standard_serving_g_positive"),
        sa.CheckConstraint("calories_per_100g >= 0", name="ck_menus_calories_nonnegative"),
        sa.CheckConstraint("carbohydrate_per_100g >= 0", name="ck_menus_carbohydrate_nonnegative"),
        sa.CheckConstraint("protein_per_100g >= 0", name="ck_menus_protein_nonnegative"),
        sa.CheckConstraint("fat_per_100g >= 0", name="ck_menus_fat_nonnegative"),
    )
    op.create_index("ix_menus_name", "menus", ["name"], unique=True)

    op.create_table(
        "user_allergies",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allergen_id", bigint_pk, sa.ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "allergen_id", name="uq_user_allergy"),
    )
    op.create_index("ix_user_allergies_user_id", "user_allergies", ["user_id"], unique=False)
    op.create_index("ix_user_allergies_allergen_id", "user_allergies", ["allergen_id"], unique=False)

    op.create_table(
        "menu_ingredients",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("menu_id", bigint_pk, sa.ForeignKey("menus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingredient_id", bigint_pk, sa.ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("menu_id", "ingredient_id", name="uq_menu_ingredient"),
    )
    op.create_index("ix_menu_ingredients_menu_id", "menu_ingredients", ["menu_id"], unique=False)
    op.create_index("ix_menu_ingredients_ingredient_id", "menu_ingredients", ["ingredient_id"], unique=False)

    op.create_table(
        "menu_allergens",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("menu_id", bigint_pk, sa.ForeignKey("menus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allergen_id", bigint_pk, sa.ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("menu_id", "allergen_id", name="uq_menu_allergen"),
    )
    op.create_index("ix_menu_allergens_menu_id", "menu_allergens", ["menu_id"], unique=False)
    op.create_index("ix_menu_allergens_allergen_id", "menu_allergens", ["allergen_id"], unique=False)

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
        "meal_menu_items",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_id", bigint_pk, sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("menu_id", bigint_pk, sa.ForeignKey("menus.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("meal_id", "menu_id", name="uq_meal_menu_item"),
    )
    op.create_index("ix_meal_menu_items_meal_id", "meal_menu_items", ["meal_id"], unique=False)
    op.create_index("ix_meal_menu_items_menu_id", "meal_menu_items", ["menu_id"], unique=False)

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
        "meal_records",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_id", bigint_pk, sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
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
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meal_record_id", "image_type", name="uq_meal_image_record_type"),
    )
    op.create_index("ix_meal_images_meal_record_id", "meal_images", ["meal_record_id"], unique=False)

    op.create_table(
        "meal_item_records",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("meal_record_id", bigint_pk, sa.ForeignKey("meal_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_menu_item_id", bigint_pk, sa.ForeignKey("meal_menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumed_ratio", sa.Float(), nullable=False),
        sa.Column("consumption_level", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_corrected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrected_by", bigint_pk, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("analysis_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meal_record_id", "meal_menu_item_id", name="uq_meal_item_record"),
        sa.CheckConstraint("consumed_ratio >= 0 AND consumed_ratio <= 1", name="ck_meal_item_records_consumed_ratio_range"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_meal_item_records_confidence_range"),
    )
    op.create_index("ix_meal_item_records_meal_record_id", "meal_item_records", ["meal_record_id"], unique=False)
    op.create_index("ix_meal_item_records_meal_menu_item_id", "meal_item_records", ["meal_menu_item_id"], unique=False)

    op.create_table(
        "serving_recommendations",
        sa.Column("id", bigint_pk, primary_key=True, autoincrement=True),
        sa.Column("user_id", bigint_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_id", bigint_pk, sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_menu_item_id", bigint_pk, sa.ForeignKey("meal_menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_level", sa.String(length=20), nullable=False),
        sa.Column("recommended_serving_ratio", sa.Float(), nullable=False),
        sa.Column("recommended_serving_g", sa.Float(), nullable=False),
        sa.Column("recent_average_consumed_ratio", sa.Float(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "meal_id", "meal_menu_item_id", name="uq_serving_recommendation_user_meal_item"),
        sa.CheckConstraint("recommended_serving_ratio > 0", name="ck_serving_recommendations_ratio_positive"),
        sa.CheckConstraint("recommended_serving_g >= 0", name="ck_serving_recommendations_serving_g_nonnegative"),
        sa.CheckConstraint(
            "recent_average_consumed_ratio IS NULL OR (recent_average_consumed_ratio >= 0 AND recent_average_consumed_ratio <= 1)",
            name="ck_serving_recommendations_recent_avg_range",
        ),
        sa.CheckConstraint("sample_count >= 0", name="ck_serving_recommendations_sample_count_nonnegative"),
    )
    op.create_index("ix_serving_recommendations_user_id", "serving_recommendations", ["user_id"], unique=False)
    op.create_index("ix_serving_recommendations_meal_id", "serving_recommendations", ["meal_id"], unique=False)
    op.create_index("ix_serving_recommendations_meal_menu_item_id", "serving_recommendations", ["meal_menu_item_id"], unique=False)


def downgrade() -> None:
    op.drop_table("serving_recommendations")
    op.drop_table("meal_item_records")
    op.drop_table("meal_images")
    op.drop_table("meal_records")
    op.drop_table("rfid_cards")
    op.drop_table("meal_menu_items")
    op.drop_table("meals")
    op.drop_table("menu_allergens")
    op.drop_table("menu_ingredients")
    op.drop_table("user_allergies")
    op.drop_table("menus")
    op.drop_table("ingredients")
    op.drop_table("allergens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
