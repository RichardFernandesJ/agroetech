"""Plantio de uma cultura em um talhão da propriedade.

Um plantio pode gerar várias colheitas (culturas recorrentes). ``stored_cycles``
representa colheitas já maduras que aguardam o jogador coletar; é o que permite
a produção offline com teto.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.game.status import PlantingStatus
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property


class Planting(Base, TimestampMixin):
    __tablename__ = "plantings"
    __table_args__ = (
        CheckConstraint("plot_index >= 0", name="ck_plantings_plot_index_non_negative"),
        CheckConstraint("cycles_done >= 0", name="ck_plantings_cycles_done_non_negative"),
        CheckConstraint("stored_cycles >= 0", name="ck_plantings_stored_cycles_non_negative"),
        Index("ix_plantings_property_status", "property_id", "status"),
        # Garante, no banco, um único plantio ativo por talhão. Plantios
        # esgotados permanecem como histórico e liberam o talhão.
        Index(
            "uq_plantings_active_plot",
            "property_id",
            "plot_index",
            unique=True,
            postgresql_where=text("status <> 'exhausted'"),
            sqlite_where=text("status <> 'exhausted'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    crop_id: Mapped[str] = mapped_column(String(40), nullable=False)
    plot_index: Mapped[int] = mapped_column(Integer, nullable=False)

    planted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_ready_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cycles_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stored_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=PlantingStatus.GROWING.value,
        nullable=False,
    )

    property: Mapped[Property] = relationship(back_populates="plantings")
