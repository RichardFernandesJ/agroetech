"""Trabalho de fabricação em uma estação (ProductionJobs).

O resultado (quantidade e horário de término) é definido ao iniciar, com os
bônus vigentes naquele momento; trocar de talentos depois não altera o trabalho.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
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


class ProductionJob(Base, TimestampMixin):
    __tablename__ = "production_jobs"
    __table_args__ = (
        CheckConstraint("batches >= 1", name="ck_production_jobs_batches_positive"),
        CheckConstraint("output_quantity >= 0", name="ck_production_jobs_output_non_negative"),
        UniqueConstraint("property_id", "request_key", name="uq_production_jobs_request_key"),
        Index("ix_production_jobs_property_open", "property_id", "collected_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    recipe_id: Mapped[str] = mapped_column(String(40), nullable=False)
    building_id: Mapped[str] = mapped_column(String(40), nullable=False)
    batches: Mapped[int] = mapped_column(Integer, nullable=False)
    output_item: Mapped[str] = mapped_column(String(80), nullable=False)
    output_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Chave de idempotência do cliente (reenvio não inicia outro trabalho).
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
