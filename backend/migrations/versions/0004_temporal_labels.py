"""unified temporal labels: replace periods FK with temporal_label_id

Revision ID: 0004_temporal_labels
Revises: 0003_territory_code
Create Date: 2026-05-26

Notes
-----
This migration:
1. Creates temporal_labels table (and temporal_label_kind enum).
2. Copies existing periods rows into temporal_labels with kind=named_period
   (year_from/year_to derived from the date range).
3. Adds migration_flows.temporal_label_id, backfills from period_id.
4. Drops migration_flows.period_id and the periods table.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_temporal_labels"
down_revision = "0003_territory_code"
branch_labels = None
depends_on = None


temporal_label_kind = sa.Enum(
    "year", "decade", "quarter_century", "half_century",
    "century", "era_label", "named_period",
    name="temporal_label_kind",
)


def upgrade() -> None:
    op.create_table(
        "temporal_labels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("kind", temporal_label_kind, nullable=False, index=True),
        sa.Column("year_from", sa.Integer, nullable=False, index=True),
        sa.Column("year_to", sa.Integer, nullable=False, index=True),
        sa.Column("description", sa.Text),
    )

    # Copy existing periods → temporal_labels as named_period
    op.execute("""
        INSERT INTO temporal_labels (slug, label, kind, year_from, year_to, description)
        SELECT slug,
               name,
               'named_period',
               EXTRACT(YEAR FROM date_from)::int,
               EXTRACT(YEAR FROM date_to)::int,
               description
        FROM periods
    """)

    # Add new FK column on migration_flows
    op.add_column(
        "migration_flows",
        sa.Column("temporal_label_id", sa.Integer, nullable=True),
    )
    op.create_foreign_key(
        "fk_migration_flows_temporal_label",
        "migration_flows", "temporal_labels",
        ["temporal_label_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_migration_flows_temporal_label_id",
        "migration_flows", ["temporal_label_id"],
    )

    # Backfill from period_id via slug join (safe: periods.slug = temporal_labels.slug)
    op.execute("""
        UPDATE migration_flows AS mf
        SET temporal_label_id = tl.id
        FROM periods p
        JOIN temporal_labels tl ON tl.slug = p.slug
        WHERE mf.period_id = p.id
    """)

    # Drop the legacy FK + column + table
    op.drop_index("ix_migration_flows_period_id", table_name="migration_flows")
    op.drop_constraint(
        "migration_flows_period_id_fkey", "migration_flows", type_="foreignkey"
    )
    op.drop_column("migration_flows", "period_id")
    op.drop_table("periods")


def downgrade() -> None:
    # Recreate periods (data not restored beyond named_period entries)
    op.create_table(
        "periods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_from", sa.Date, nullable=False),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("description", sa.Text),
    )
    op.execute("""
        INSERT INTO periods (slug, name, date_from, date_to, description)
        SELECT slug, label,
               make_date(year_from, 1, 1),
               make_date(year_to, 12, 31),
               description
        FROM temporal_labels
        WHERE kind = 'named_period'
    """)

    op.add_column(
        "migration_flows",
        sa.Column("period_id", sa.Integer, nullable=True),
    )
    op.create_foreign_key(
        "migration_flows_period_id_fkey",
        "migration_flows", "periods",
        ["period_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_migration_flows_period_id", "migration_flows", ["period_id"]
    )
    op.execute("""
        UPDATE migration_flows AS mf
        SET period_id = p.id
        FROM temporal_labels tl
        JOIN periods p ON p.slug = tl.slug
        WHERE mf.temporal_label_id = tl.id
    """)

    op.drop_index("ix_migration_flows_temporal_label_id", table_name="migration_flows")
    op.drop_constraint(
        "fk_migration_flows_temporal_label", "migration_flows", type_="foreignkey"
    )
    op.drop_column("migration_flows", "temporal_label_id")
    op.drop_table("temporal_labels")
    temporal_label_kind.drop(op.get_bind(), checkfirst=True)
