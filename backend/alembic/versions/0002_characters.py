"""Personagens e posição no mundo.

Revision ID: 0002_characters
Revises: 0001_foundation
Create Date: 2026-11-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_characters"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("skin_tone", sa.String(length=20), nullable=False),
        sa.Column("hair_style", sa.String(length=20), nullable=False),
        sa.Column("outfit_color", sa.String(length=7), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("facing", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position_x >= 0",
            name="ck_characters_position_x_non_negative",
        ),
        sa.CheckConstraint(
            "position_y >= 0",
            name="ck_characters_position_y_non_negative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_characters_user_id"),
    )
    op.create_index("ix_characters_property_id", "characters", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_characters_property_id", table_name="characters")
    op.drop_table("characters")
