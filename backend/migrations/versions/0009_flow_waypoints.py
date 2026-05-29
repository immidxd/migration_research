"""flow_waypoints — ordered transit points on a flow (Group E)

Revision ID: 0009_flow_waypoints
Revises: 0008_flow_share_quantity
Create Date: 2026-05-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0009_flow_waypoints"
down_revision = "0008_flow_share_quantity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flow_waypoints",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "flow_id", sa.Integer,
            sa.ForeignKey("migration_flows.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column(
            "territory_id", sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        ),
        sa.Column("note", sa.Text),
        sa.UniqueConstraint("flow_id", "sequence_no", name="uq_flow_waypoint_order"),
    )


def downgrade() -> None:
    op.drop_table("flow_waypoints")
