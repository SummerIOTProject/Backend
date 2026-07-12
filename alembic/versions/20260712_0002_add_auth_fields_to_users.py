"""add auth fields to users

Revision ID: 20260712_0002
Revises: 20260712_0001
Create Date: 2026-07-12 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0002"
down_revision = "20260712_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("hashed_password", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("role", sa.String(length=20), nullable=False, server_default="STUDENT"))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.create_index("ix_users_email", ["email"], unique=True)

    op.execute("UPDATE users SET email = student_number || '@example.com' WHERE email IS NULL")
    op.execute("UPDATE users SET hashed_password = 'legacy-account' WHERE hashed_password IS NULL")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("hashed_password", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("is_active")
        batch_op.drop_column("role")
        batch_op.drop_column("hashed_password")
        batch_op.drop_column("email")
