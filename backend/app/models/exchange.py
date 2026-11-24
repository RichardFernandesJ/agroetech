"""Anúncios do mercado entre jogadores e o histórico comercial.

Entidades ``MarketListings`` e ``MarketTransactions`` do AGENTS.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MarketListing(Base, TimestampMixin):
    """Anúncio com os itens em custódia (saem do inventário ao anunciar)."""

    __tablename__ = "market_listings"
    __table_args__ = (
        CheckConstraint("unit_price >= 1", name="ck_market_listings_price_positive"),
        CheckConstraint(
            "quantity_remaining >= 0", name="ck_market_listings_remaining_non_negative"
        ),
        CheckConstraint(
            "quantity_remaining <= quantity_initial", name="ck_market_listings_remaining_le_initial"
        ),
        UniqueConstraint("seller_id", "request_key", name="uq_market_listings_request_key"),
        Index("ix_market_listings_browse", "status", "item_id", "unit_price"),
        Index("ix_market_listings_seller_status", "seller_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Onde os itens voltam se o anúncio for cancelado ou expirar.
    seller_property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity_initial: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    # active | sold | cancelled | expired
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)


class MarketTransaction(Base, TimestampMixin):
    """Histórico comercial: cada compra (inclusive parcial) é uma linha imutável."""

    __tablename__ = "market_transactions"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_market_transactions_quantity_positive"),
        UniqueConstraint("buyer_id", "request_key", name="uq_market_transactions_request_key"),
        Index("ix_market_transactions_buyer", "buyer_id", "created_at"),
        Index("ix_market_transactions_seller", "seller_id", "created_at"),
        Index("ix_market_transactions_item", "item_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    gross: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_net: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Chave de idempotência do comprador (reenvio não compra duas vezes).
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
