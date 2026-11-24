"""Trabalhos de fabricação (ProductionJobs).

Revision ID: 0008_production_jobs
Revises: 0007_animals
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_production_jobs"
down_revision: str | None = "0007_animals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("recipe_id", sa.String(length=40), nullable=False),
        sa.Column("building_id", sa.String(length=40), nullable=False),
        sa.Column("batches", sa.Integer(), nullable=False),
        sa.Column("output_item", sa.String(length=80), nullable=False),
        sa.Column("output_quantity", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finish_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("batches >= 1", name="ck_production_jobs_batches_positive"),
        sa.CheckConstraint("output_quantity >= 0", name="ck_production_jobs_output_non_negative"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "request_key", name="uq_production_jobs_request_key"),
    )
    op.create_index("ix_production_jobs_property_id", "production_jobs", ["property_id"])
    op.create_index(
        "ix_production_jobs_property_open", "production_jobs", ["property_id", "collected_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_production_jobs_property_open", table_name="production_jobs")
    op.drop_index("ix_production_jobs_property_id", table_name="production_jobs")
    op.drop_table("production_jobs")
