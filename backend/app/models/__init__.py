"""Importa todos os models para que o metadata seja registrado."""

from app.models.base import Base
from app.models.character import Character
from app.models.inventory import InventoryItem
from app.models.planting import Planting
from app.models.property import Property
from app.models.user import User

__all__ = ["Base", "Character", "InventoryItem", "Planting", "Property", "User"]
