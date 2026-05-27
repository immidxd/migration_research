"""widen territories.code to 160 chars (uezd slugs from RiStat 1897 import)

Revision ID: 0005_widen_territory_code
Revises: 0004_temporal_labels
Create Date: 2026-05-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_widen_territory_code"
down_revision = "0004_temporal_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "territories", "code",
        existing_type=sa.String(64),
        type_=sa.String(160),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "territories", "code",
        existing_type=sa.String(160),
        type_=sa.String(64),
        existing_nullable=True,
    )
