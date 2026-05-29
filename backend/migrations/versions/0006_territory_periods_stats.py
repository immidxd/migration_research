"""territory periods (time-varying status) + territorial stock stats

Revision ID: 0006_territory_periods_stats
Revises: 0005_widen_territory_code
Create Date: 2026-05-29

Adds:
- territory_periods: period-scoped status/name/sovereign of a territory
  (e.g. Kingdom of Hawaii -> US Territory), so one row keeps one geometry.
- territory_stats: stock/snapshot facts ("10,000 Ukrainians in Canada, 1908").
- link tables territory_period_sources / territory_stat_sources.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0006_territory_periods_stats"
down_revision = "0005_widen_territory_code"
branch_labels = None
depends_on = None


stat_kind = sa.Enum(
    "diaspora_stock", "total_population", "immigrant_arrivals", "other",
    name="stat_kind",
)
# count_method already exists (created with migration_flows); reference the
# existing Postgres type without re-issuing CREATE TYPE.
count_method = postgresql.ENUM(
    "exact", "estimate", "range", "unknown",
    name="count_method", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "territory_periods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "territory_id", sa.Integer,
            sa.ForeignKey("territories.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("year_from", sa.Integer, nullable=False, index=True),
        sa.Column("year_to", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.String(255)),
        sa.Column("name", sa.String(255)),
        sa.Column("name_local", sa.String(255)),
        sa.Column(
            "sovereign_id", sa.Integer,
            sa.ForeignKey("territories.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "territory_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "territory_id", sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        ),
        sa.Column("stat_kind", stat_kind, nullable=False, index=True),
        sa.Column("group_label", sa.String(255)),
        sa.Column("as_of_year", sa.Integer, index=True),
        sa.Column(
            "temporal_label_id", sa.Integer,
            sa.ForeignKey("temporal_labels.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("count", sa.Integer),
        sa.Column("count_lower", sa.Integer),
        sa.Column("count_upper", sa.Integer),
        sa.Column("count_method", count_method, server_default="unknown", nullable=False),
        sa.Column("provisional", sa.Boolean, server_default="false", nullable=False, index=True),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "territory_period_sources",
        sa.Column(
            "period_id", sa.Integer,
            sa.ForeignKey("territory_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id", sa.Integer,
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.Text),
        sa.PrimaryKeyConstraint("period_id", "source_id"),
    )

    op.create_table(
        "territory_stat_sources",
        sa.Column(
            "stat_id", sa.Integer,
            sa.ForeignKey("territory_stats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id", sa.Integer,
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.Text),
        sa.PrimaryKeyConstraint("stat_id", "source_id"),
    )


def downgrade() -> None:
    op.drop_table("territory_stat_sources")
    op.drop_table("territory_period_sources")
    op.drop_table("territory_stats")
    op.drop_table("territory_periods")
    stat_kind.drop(op.get_bind(), checkfirst=True)
