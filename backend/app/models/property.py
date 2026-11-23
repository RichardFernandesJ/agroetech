"""Propriedade rural pertencente a um jogador."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.planting import Planting
    from app.models.user import User


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    plot_count: Mapped[int] = mapped_column(Integer, default=6, nullable=False)

    # Marca a última vez que a produção offline foi simulada para esta fazenda.
    last_production_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    owner: Mapped[User] = relationship(back_populates="properties")
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
    )
    plantings: Mapped[list[Planting]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
    )
