"""Importa todos os models para que o metadata seja registrado."""

from app.models.animal import Animal
from app.models.base import Base
from app.models.building import Building
from app.models.character import Character
from app.models.inventory import InventoryItem
from app.models.planting import Planting
from app.models.production_job import ProductionJob
from app.models.progress import PlayerProgress
from app.models.property import Property
from app.models.talent import PresetNode, TalentPreset, TalentRespec
from app.models.user import User
from app.models.wallet import Wallet, WalletLedgerEntry

__all__ = [
    "Animal",
    "Base",
    "Building",
    "Character",
    "InventoryItem",
    "Planting",
    "PresetNode",
    "ProductionJob",
    "TalentPreset",
    "TalentRespec",
    "PlayerProgress",
    "Property",
    "User",
    "Wallet",
    "WalletLedgerEntry",
]
