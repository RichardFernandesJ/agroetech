"""Trocas diretas entre jogadores.

Revision ID: 0012_trades
Revises: 0011_exchange
Create Date: 2026-11-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_trades"
down_revision: str | None = "0011_exchange"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_offers",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("proposer_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("recipient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("proposer_property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("offer_agc", sa.BigInteger(), nullable=False),
        sa.Column("request_agc", sa.BigInteger(), nullable=False),
        sa.Column("proposer_fee", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("offer_agc >= 0", name="ck_trade_offers_offer_agc_non_negative"),
        sa.CheckConstraint("request_agc >= 0", name="ck_trade_offers_request_agc_non_negative"),
        sa.CheckConstraint("proposer_id <> recipient_id", name="ck_trade_offers_distinct_players"),
        sa.ForeignKeyConstraint(["proposer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposer_id", "request_key", name="uq_trade_offers_request_key"),
    )
    op.create_index("ix_trade_offers_recipient_status", "trade_offers", ["recipient_id", "status"])
    op.create_index("ix_trade_offers_proposer_status", "trade_offers", ["proposer_id", "status"])

    op.create_table(
        "trade_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("offer_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("item_id", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_trade_items_quantity_positive"),
        sa.ForeignKeyConstraint(["offer_id"], ["trade_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id", "side", "item_id", name="uq_trade_items_offer_side_item"),
    )
    op.create_index("ix_trade_items_offer_id", "trade_items", ["offer_id"])


def downgrade() -> None:
    op.drop_index("ix_trade_items_offer_id", table_name="trade_items")
    op.drop_table("trade_items")
    op.drop_index("ix_trade_offers_proposer_status", table_name="trade_offers")
    op.drop_index("ix_trade_offers_recipient_status", table_name="trade_offers")
    op.drop_table("trade_offers")
