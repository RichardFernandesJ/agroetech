"""Status de um plantio (também usado pela lógica de jogo)."""

from enum import StrEnum


class PlantingStatus(StrEnum):
    GROWING = "growing"
    READY = "ready"
    EXHAUSTED = "exhausted"
