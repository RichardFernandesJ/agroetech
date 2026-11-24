"""Mercado entre jogadores: anúncios e histórico comercial.

Revision ID: 0011_exchange
Revises: 0010_one_property_per_user
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_exchange"
down_revision: str | None = "0010_one_property_per_user"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_listings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("seller_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("seller_property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=80), nullable=False),
        sa.Column("quantity_initial", sa.Integer(), nullable=False),
        sa.Column("quantity_remaining", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_price >= 1", name="ck_market_listings_price_positive"),
        sa.CheckConstraint(
            "quantity_remaining >= 0", name="ck_market_listings_remaining_non_negative"
        ),
        sa.CheckConstraint(
            "quantity_remaining <= quantity_initial", name="ck_market_listings_remaining_le_initial"
        ),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seller_id", "request_key", name="uq_market_listings_request_key"),
    )
    op.create_index(
        "ix_market_listings_browse", "market_listings", ["status", "item_id", "unit_price"]
    )
    op.create_index("ix_market_listings_seller_status", "market_listings", ["seller_id", "status"])

    op.create_table(
        "market_transactions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("listing_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("buyer_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("seller_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("gross", sa.BigInteger(), nullable=False),
        sa.Column("fee", sa.BigInteger(), nullable=False),
        sa.Column("seller_net", sa.BigInteger(), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_market_transactions_quantity_positive"),
        sa.ForeignKeyConstraint(["listing_id"], ["market_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buyer_id", "request_key", name="uq_market_transactions_request_key"),
    )
    op.create_index("ix_market_transactions_listing_id", "market_transactions", ["listing_id"])
    op.create_index(
        "ix_market_transactions_buyer", "market_transactions", ["buyer_id", "created_at"]
    )
    op.create_index(
        "ix_market_transactions_seller", "market_transactions", ["seller_id", "created_at"]
    )
    op.create_index("ix_market_transactions_item", "market_transactions", ["item_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_market_transactions_item", table_name="market_transactions")
    op.drop_index("ix_market_transactions_seller", table_name="market_transactions")
    op.drop_index("ix_market_transactions_buyer", table_name="market_transactions")
    op.drop_index("ix_market_transactions_listing_id", table_name="market_transactions")
    op.drop_table("market_transactions")
    op.drop_index("ix_market_listings_seller_status", table_name="market_listings")
    op.drop_index("ix_market_listings_browse", table_name="market_listings")
    op.drop_table("market_listings")
