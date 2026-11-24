"""Animais.

Revision ID: 0007_animals
Revises: 0006_buildings
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_animals"
down_revision: str | None = "0006_buildings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "animals",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("species", sa.String(length=30), nullable=False),
        sa.Column("fed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("progress_seconds", sa.Float(), nullable=False),
        sa.Column("stored", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stored >= 0", name="ck_animals_stored_non_negative"),
        sa.CheckConstraint("progress_seconds >= 0", name="ck_animals_progress_non_negative"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_animals_property_id", "animals", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_animals_property_id", table_name="animals")
    op.drop_table("animals")
