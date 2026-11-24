"""Nível de uma construção em uma propriedade (uma linha por construção melhorada)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint("property_id", "building_id", name="uq_buildings_property_building"),
        CheckConstraint("level >= 0", name="ck_buildings_level_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    building_id: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
