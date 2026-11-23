"""Schemas da carteira de AgroCoin."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class WalletRead(BaseModel):
    id: uuid.UUID
    balance: int
    currency: str = "AGC"


class LedgerEntryRead(BaseModel):
    id: uuid.UUID
    kind: str
    amount: int
    balance_after: int
    item_id: str | None
    item_name: str | None
    quantity: int | None
    unit_price: int | None
    fee: int
    created_at: datetime


class LedgerPage(BaseModel):
    entries: list[LedgerEntryRead]
    limit: int
    offset: int
