"""Uma fazenda por jogador, garantida no banco.

Revision ID: 0010_one_property_per_user
Revises: 0009_animal_modifiers
Create Date: 2026-11-23

Troca o índice comum de ``properties.owner_id`` por um índice único. Se já
existirem jogadores com mais de uma fazenda (criadas antes da regra), a migração
falha com uma mensagem clara em vez de apagar dados: resolva-os manualmente.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_one_property_per_user"
down_revision: str | None = "0009_animal_modifiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicated = (
        op.get_bind()
        .execute(
            sa.text("select owner_id from properties group by owner_id having count(*) > 1 limit 1")
        )
        .first()
    )
    if duplicated is not None:
        raise RuntimeError(
            "Há jogadores com mais de uma fazenda. Una ou remova as extras antes de aplicar "
            "a migração 0010 (a regra agora é uma fazenda por jogador)."
        )
    op.drop_index("ix_properties_owner_id", table_name="properties")
    op.create_index("uq_properties_owner", "properties", ["owner_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_properties_owner", table_name="properties")
    op.create_index("ix_properties_owner_id", "properties", ["owner_id"])
