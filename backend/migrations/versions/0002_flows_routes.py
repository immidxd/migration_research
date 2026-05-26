"""second-wave: flows, events, routes, segments, transit profiles, source links

Revision ID: 0002_flows_routes
Revises: 0001_init
Create Date: 2026-05-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry


revision = "0002_flows_routes"
down_revision = "0001_init"
branch_labels = None
depends_on = None


# Shared Enum instances — first column reference will emit CREATE TYPE.
precision_level = sa.Enum(
    "point", "settlement", "volost", "uezd", "gubernia",
    "region", "country", "vague",
    name="precision_level",
)
migration_vector = sa.Enum(
    "transatlantic", "european", "intra_imperial_east",
    "intra_imperial_other", "internal",
    name="migration_vector",
)
transport_mode = sa.Enum(
    "land", "rail", "river", "sea", "mixed", "unknown",
    name="transport_mode",
)
date_precision = sa.Enum(
    "day", "month", "year", "decade", "period", "unknown",
    name="date_precision",
)
count_method = sa.Enum(
    "exact", "estimate", "range", "unknown",
    name="count_method",
)


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("vector", migration_vector, nullable=False, index=True),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "route_segments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "route_id",
            sa.Integer,
            sa.ForeignKey("routes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column(
            "from_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "to_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("transport_mode", transport_mode, nullable=False),
        sa.Column(
            "geom",
            Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True),
        ),
        sa.Column("date_from", sa.Date),
        sa.Column("date_to", sa.Date),
        sa.Column("notes", sa.Text),
        sa.UniqueConstraint("route_id", "sequence_no", name="uq_route_segment_order"),
    )

    op.create_table(
        "migration_flows",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "origin_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "destination_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "period_id",
            sa.Integer,
            sa.ForeignKey("periods.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("date_from", sa.Date),
        sa.Column("date_to", sa.Date),
        sa.Column("date_precision", date_precision, nullable=False, server_default="unknown"),
        sa.Column("count", sa.Integer),
        sa.Column("count_lower", sa.Integer),
        sa.Column("count_upper", sa.Integer),
        sa.Column("count_method", count_method, nullable=False, server_default="unknown"),
        sa.Column("vector", migration_vector, nullable=False, index=True),
        sa.Column("transport_mode", transport_mode, nullable=False, server_default="unknown"),
        sa.Column("origin_precision", precision_level, nullable=False),
        sa.Column(
            "destination_precision", precision_level, nullable=False, server_default="country"
        ),
        sa.Column(
            "provisional", sa.Boolean, nullable=False, server_default=sa.false(), index=True
        ),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "migration_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.String(255)),
        sa.Column(
            "origin_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "destination_territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "route_id",
            sa.Integer,
            sa.ForeignKey("routes.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("event_date", sa.Date, index=True),
        sa.Column("date_precision", date_precision, nullable=False, server_default="unknown"),
        sa.Column("people_count", sa.Integer),
        sa.Column("vector", migration_vector, nullable=False, index=True),
        sa.Column("transport_mode", transport_mode, nullable=False, server_default="unknown"),
        sa.Column("origin_precision", precision_level, nullable=False),
        sa.Column(
            "destination_precision", precision_level, nullable=False, server_default="country"
        ),
        sa.Column(
            "provisional", sa.Boolean, nullable=False, server_default=sa.false(), index=True
        ),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "transit_point_profiles",
        sa.Column(
            "territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("active_from", sa.Date),
        sa.Column("active_to", sa.Date),
        sa.Column("operator", sa.String(255)),
        sa.Column("notes", sa.Text),
    )

    # --- Source link tables ---
    for table, parent_col, parent_table in [
        ("flow_sources", "flow_id", "migration_flows"),
        ("event_sources", "event_id", "migration_events"),
        ("route_sources", "route_id", "routes"),
        ("territory_sources", "territory_id", "territories"),
        ("alias_sources", "alias_id", "territory_aliases"),
    ]:
        op.create_table(
            table,
            sa.Column(
                parent_col,
                sa.Integer,
                sa.ForeignKey(f"{parent_table}.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "source_id",
                sa.Integer,
                sa.ForeignKey("sources.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("note", sa.Text),
            sa.PrimaryKeyConstraint(parent_col, "source_id"),
        )


def downgrade() -> None:
    for table in [
        "alias_sources",
        "territory_sources",
        "route_sources",
        "event_sources",
        "flow_sources",
        "transit_point_profiles",
        "migration_events",
        "migration_flows",
        "route_segments",
        "routes",
    ]:
        op.drop_table(table)

    bind = op.get_bind()
    for et in (count_method, date_precision, transport_mode, migration_vector, precision_level):
        et.drop(bind, checkfirst=True)
