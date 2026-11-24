"""Bônus de talentos gravados em cada animal.

Revision ID: 0009_animal_modifiers
Revises: 0008_production_jobs
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_animal_modifiers"
down_revision: str | None = "0008_production_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "animals", sa.Column("speed_bp", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "animals", sa.Column("yield_bp", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    with op.batch_alter_table("animals") as batch:
        batch.drop_column("yield_bp")
        batch.drop_column("speed_bp")
