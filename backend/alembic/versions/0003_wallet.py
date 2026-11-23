"""Carteira de AgroCoin e livro-razão.

Revision ID: 0003_wallet
Revises: 0002_characters
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_wallet"
down_revision: str | None = "0002_characters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("balance", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
    )
    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("wallet_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price", sa.Integer(), nullable=True),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_wallet_ledger_balance_non_negative",
        ),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wallet_id", "idempotency_key", name="uq_wallet_ledger_idempotency"),
    )
    op.create_index("ix_wallet_ledger_wallet_id", "wallet_ledger", ["wallet_id"])


def downgrade() -> None:
    op.drop_index("ix_wallet_ledger_wallet_id", table_name="wallet_ledger")
    op.drop_table("wallet_ledger")
    op.drop_table("wallets")
