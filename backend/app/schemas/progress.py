"""Schemas de progressão."""

from pydantic import BaseModel


class ProgressRead(BaseModel):
    level: int
    xp: int
    xp_into_level: int
    # XP necessário neste nível para o próximo (None no nível máximo).
    xp_for_next: int | None
    max_level: int
