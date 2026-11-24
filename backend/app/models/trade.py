"""Trocas diretas entre jogadores (entidades TradeOffers e TradeItems do AGENTS.md)."""

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


class TradeOffer(Base, TimestampMixin):
    """Proposta de troca. O lado do proponente fica em custódia enquanto ela estiver pendente."""

    __tablename__ = "trade_offers"
    __table_args__ = (
        CheckConstraint("offer_agc >= 0", name="ck_trade_offers_offer_agc_non_negative"),
        CheckConstraint("request_agc >= 0", name="ck_trade_offers_request_agc_non_negative"),
        CheckConstraint("proposer_id <> recipient_id", name="ck_trade_offers_distinct_players"),
        UniqueConstraint("proposer_id", "request_key", name="uq_trade_offers_request_key"),
        Index("ix_trade_offers_recipient_status", "recipient_id", "status"),
        Index("ix_trade_offers_proposer_status", "proposer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Para onde voltam (ou vão) os itens do proponente.
    proposer_property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    # pending | accepted | declined | cancelled | expired
    status: Mapped[str] = mapped_column(String(12), default="pending", nullable=False)
    offer_agc: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    request_agc: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # Taxa do proponente, paga na criação e devolvida se não houver troca.
    proposer_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TradeItem(Base, TimestampMixin):
    """Linha de item de uma proposta: ``offer`` (do proponente) ou ``request`` (do destinatário)."""

    __tablename__ = "trade_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_trade_items_quantity_positive"),
        UniqueConstraint("offer_id", "side", "item_id", name="uq_trade_items_offer_side_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trade_offers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    item_id: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
