"""flow share quantity — count_method=share + explicit base (Group E)

Revision ID: 0008_flow_share_quantity
Revises: 0007_flow_relations
Create Date: 2026-05-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_flow_share_quantity"
down_revision = "0007_flow_relations"
branch_labels = None
depends_on = None


share_base_kind = sa.Enum(
    "flow", "population", "migration_aggregate",
    name="share_base_kind",
)


def upgrade() -> None:
    # Extend the existing count_method enum with 'share'.
    op.execute("ALTER TYPE count_method ADD VALUE IF NOT EXISTS 'share'")

    share_base_kind.create(op.get_bind(), checkfirst=True)

    op.add_column("migration_flows", sa.Column("share_pct", sa.Float))
    op.add_column("migration_flows", sa.Column("share_pct_lower", sa.Float))
    op.add_column("migration_flows", sa.Column("share_pct_upper", sa.Float))
    op.add_column("migration_flows", sa.Column("share_base_kind", share_base_kind))
    op.add_column(
        "migration_flows",
        sa.Column(
            "share_base_flow_id", sa.Integer,
            sa.ForeignKey("migration_flows.id", ondelete="SET NULL"), index=True,
        ),
    )
    op.add_column(
        "migration_flows",
        sa.Column(
            "share_base_territory_id", sa.Integer,
            sa.ForeignKey("territories.id", ondelete="SET NULL"), index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("migration_flows", "share_base_territory_id")
    op.drop_column("migration_flows", "share_base_flow_id")
    op.drop_column("migration_flows", "share_base_kind")
    op.drop_column("migration_flows", "share_pct_upper")
    op.drop_column("migration_flows", "share_pct_lower")
    op.drop_column("migration_flows", "share_pct")
    share_base_kind.drop(op.get_bind(), checkfirst=True)
    # Note: a value cannot be removed from a Postgres enum; 'share' stays on
    # count_method. Harmless (no rows use it after downgrade).
