"""Schemas da produção offline."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class OfflineSyncRead(BaseModel):
    property_id: uuid.UUID
    synced_at: datetime
    window_start: datetime
    offline_seconds: int
    plantings_synced: int
    cycles_stored: int
    ready_plantings: int
