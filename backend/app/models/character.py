"""Personagem do jogador no mundo.

Cada conta possui no máximo um personagem (constraint única em ``user_id``).
O personagem pertence a uma propriedade e guarda a última posição conhecida,
que o cliente usa para restaurar o estado ao entrar.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.game.world import DEFAULT_FACING, SPAWN_X, SPAWN_Y
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.user import User


class Character(Base, TimestampMixin):
    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_characters_user_id"),
        CheckConstraint("position_x >= 0", name="ck_characters_position_x_non_negative"),
        CheckConstraint("position_y >= 0", name="ck_characters_position_y_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)

    # Aparência em presets validados pelos schemas; o cliente converte para
    # pixel art. Campos separados evitam JSON opaco no banco.
    skin_tone: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    hair_style: Mapped[str] = mapped_column(String(20), default="short", nullable=False)
    outfit_color: Mapped[str] = mapped_column(String(7), default="#3f7d4e", nullable=False)

    position_x: Mapped[float] = mapped_column(Float, default=SPAWN_X, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=SPAWN_Y, nullable=False)
    facing: Mapped[str] = mapped_column(String(8), default=DEFAULT_FACING, nullable=False)

    user: Mapped[User] = relationship(back_populates="character")
    property: Mapped[Property] = relationship(back_populates="characters")
