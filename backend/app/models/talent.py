"""Presets de talentos, nós adquiridos e auditoria de redefinições."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class TalentPreset(Base, TimestampMixin):
    __tablename__ = "talent_presets"
    __table_args__ = (
        UniqueConstraint("user_id", "slot", name="uq_talent_presets_user_slot"),
        CheckConstraint("slot >= 1", name="ck_talent_presets_slot_positive"),
        # No máximo um preset ativo por jogador (garantido no banco).
        Index(
            "uq_talent_presets_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship()
    nodes: Mapped[list[PresetNode]] = relationship(
        back_populates="preset",
        cascade="all, delete-orphan",
    )


class PresetNode(Base, TimestampMixin):
    __tablename__ = "preset_nodes"
    __table_args__ = (UniqueConstraint("preset_id", "node_id", name="uq_preset_nodes_preset_node"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_presets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(60), nullable=False)

    preset: Mapped[TalentPreset] = relationship(back_populates="nodes")


class TalentRespec(Base, TimestampMixin):
    """Auditoria: cada redefinição de talentos e o que ela custou."""

    __tablename__ = "talent_respecs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    preset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    nodes_removed: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
