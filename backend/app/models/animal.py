"""Animal de uma propriedade: alimentação, progresso de produção e estoque."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Animal(Base, TimestampMixin):
    __tablename__ = "animals"
    __table_args__ = (
        CheckConstraint("stored >= 0", name="ck_animals_stored_non_negative"),
        CheckConstraint("progress_seconds >= 0", name="ck_animals_progress_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    species: Mapped[str] = mapped_column(String(30), nullable=False)

    # Até quando o animal está alimentado (nulo = nunca foi alimentado).
    fed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Última vez que a produção foi contabilizada.
    last_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Segundos alimentados já acumulados rumo ao próximo produto.
    progress_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Produtos prontos para coleta.
    stored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
