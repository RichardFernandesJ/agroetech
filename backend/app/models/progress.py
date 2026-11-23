"""Progressão do jogador: experiência acumulada (o nível é derivado do XP)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PlayerProgress(Base, TimestampMixin):
    __tablename__ = "player_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_player_progress_user_id"),
        CheckConstraint("xp >= 0", name="ck_player_progress_xp_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    xp: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="progress")
