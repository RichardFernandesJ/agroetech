"""Usuário (jogador) da plataforma."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.progress import PlayerProgress
    from app.models.property import Property
    from app.models.wallet import Wallet


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    properties: Mapped[list[Property]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    character: Mapped[Character | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    wallet: Mapped[Wallet | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    progress: Mapped[PlayerProgress | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
