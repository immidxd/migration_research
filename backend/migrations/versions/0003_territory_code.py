"""add territories.code (external id) — ISO_A2/A3 for countries, slugs for regions

Revision ID: 0003_territory_code
Revises: 0002_flows_routes
Create Date: 2026-05-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_territory_code"
down_revision = "0002_flows_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("territories", sa.Column("code", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_territories_code", "territories", ["code"])
    op.create_index("ix_territories_code", "territories", ["code"])


def downgrade() -> None:
    op.drop_index("ix_territories_code", table_name="territories")
    op.drop_constraint("uq_territories_code", "territories", type_="unique")
    op.drop_column("territories", "code")
