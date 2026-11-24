"""Construções melhoráveis.

Revision ID: 0006_buildings
Revises: 0005_talents
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_buildings"
down_revision: str | None = "0005_talents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "buildings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("building_id", sa.String(length=40), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("level >= 0", name="ck_buildings_level_non_negative"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "building_id", name="uq_buildings_property_building"),
    )
    op.create_index("ix_buildings_property_id", "buildings", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_buildings_property_id", table_name="buildings")
    op.drop_table("buildings")
