"""Carteira de AgroCoin e livro-razão (WalletLedger).

O saldo em ``wallets`` é sempre derivável do ``wallet_ledger``: toda mudança de
saldo gera uma linha imutável com o saldo resultante, o que permite auditoria.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_wallets_user_id"),
        CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="wallet")
    entries: Mapped[list[WalletLedgerEntry]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan",
    )


class WalletLedgerEntry(Base, TimestampMixin):
    __tablename__ = "wallet_ledger"
    __table_args__ = (
        UniqueConstraint("wallet_id", "idempotency_key", name="uq_wallet_ledger_idempotency"),
        CheckConstraint("balance_after >= 0", name="ck_wallet_ledger_balance_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # initial_grant | seed_purchase | crop_sale
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    # Positivo = crédito, negativo = débito.
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    wallet: Mapped[Wallet] = relationship(back_populates="entries")
