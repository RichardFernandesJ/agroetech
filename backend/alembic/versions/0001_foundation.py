"""Fundação: usuários, propriedades, inventário e plantios.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-11-22

Este é o schema inicial do backend. A partir daqui, toda alteração estrutural
deve entrar como uma nova revisão do Alembic.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores usados pelo Alembic.
revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "properties",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("area_hectares", sa.Float(), nullable=False),
        sa.Column("plot_count", sa.Integer(), nullable=False),
        sa.Column("last_production_sync_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_owner_id", "properties", ["owner_id"])

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "item_id", name="uq_inventory_property_item"),
    )
    op.create_index("ix_inventory_items_property_id", "inventory_items", ["property_id"])

    op.create_table(
        "plantings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("crop_id", sa.String(length=40), nullable=False),
        sa.Column("plot_index", sa.Integer(), nullable=False),
        sa.Column("planted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_ready_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cycles_done", sa.Integer(), nullable=False),
        sa.Column("stored_cycles", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("plot_index >= 0", name="ck_plantings_plot_index_non_negative"),
        sa.CheckConstraint("cycles_done >= 0", name="ck_plantings_cycles_done_non_negative"),
        sa.CheckConstraint("stored_cycles >= 0", name="ck_plantings_stored_cycles_non_negative"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plantings_property_id", "plantings", ["property_id"])
    op.create_index("ix_plantings_property_status", "plantings", ["property_id", "status"])
    op.create_index(
        "uq_plantings_active_plot",
        "plantings",
        ["property_id", "plot_index"],
        unique=True,
        postgresql_where=sa.text("status <> 'exhausted'"),
        sqlite_where=sa.text("status <> 'exhausted'"),
    )


def downgrade() -> None:
    op.drop_index("uq_plantings_active_plot", table_name="plantings")
    op.drop_index("ix_plantings_property_status", table_name="plantings")
    op.drop_index("ix_plantings_property_id", table_name="plantings")
    op.drop_table("plantings")

    op.drop_index("ix_inventory_items_property_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index("ix_properties_owner_id", table_name="properties")
    op.drop_table("properties")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
