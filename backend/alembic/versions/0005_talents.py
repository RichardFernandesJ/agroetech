"""Talentos: presets, nós adquiridos, redefinições e snapshot de modificadores no plantio.

Revision ID: 0005_talents
Revises: 0004_progress
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_talents"
down_revision: str | None = "0004_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plantings", sa.Column("grow_seconds", sa.Integer(), nullable=True))
    op.add_column("plantings", sa.Column("modifiers", sa.JSON(), nullable=True))

    op.create_table(
        "talent_presets",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("slot >= 1", name="ck_talent_presets_slot_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slot", name="uq_talent_presets_user_slot"),
    )
    op.create_index("ix_talent_presets_user_id", "talent_presets", ["user_id"])
    op.create_index(
        "uq_talent_presets_active",
        "talent_presets",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )

    op.create_table(
        "preset_nodes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("preset_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["preset_id"], ["talent_presets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preset_id", "node_id", name="uq_preset_nodes_preset_node"),
    )
    op.create_index("ix_preset_nodes_preset_id", "preset_nodes", ["preset_id"])

    op.create_table(
        "talent_respecs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("preset_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("nodes_removed", sa.Integer(), nullable=False),
        sa.Column("cost", sa.BigInteger(), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_talent_respecs_user_id", "talent_respecs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_talent_respecs_user_id", table_name="talent_respecs")
    op.drop_table("talent_respecs")
    op.drop_index("ix_preset_nodes_preset_id", table_name="preset_nodes")
    op.drop_table("preset_nodes")
    op.drop_index("uq_talent_presets_active", table_name="talent_presets")
    op.drop_index("ix_talent_presets_user_id", table_name="talent_presets")
    op.drop_table("talent_presets")
    with op.batch_alter_table("plantings") as batch:
        batch.drop_column("modifiers")
        batch.drop_column("grow_seconds")
