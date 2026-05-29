"""flow_relations — declared relationships between flows (Group E core)

Revision ID: 0007_flow_relations
Revises: 0006_territory_periods_stats
Create Date: 2026-05-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007_flow_relations"
down_revision = "0006_territory_periods_stats"
branch_labels = None
depends_on = None


relation_kind = sa.Enum(
    "contains", "equals", "disjoint", "overlaps_unknown",
    name="relation_kind",
)


def upgrade() -> None:
    op.create_table(
        "flow_relations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "from_flow_id", sa.Integer,
            sa.ForeignKey("migration_flows.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "to_flow_id", sa.Integer,
            sa.ForeignKey("migration_flows.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("kind", relation_kind, nullable=False, index=True),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("from_flow_id", "to_flow_id", "kind", name="uq_flow_relation"),
        sa.CheckConstraint("from_flow_id <> to_flow_id", name="ck_flow_relation_no_self"),
    )


def downgrade() -> None:
    op.drop_table("flow_relations")
    relation_kind.drop(op.get_bind(), checkfirst=True)
