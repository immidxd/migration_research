"""init schema: extensions + territories, periods, sources

Revision ID: 0001_init
Revises:
Create Date: 2026-05-26

Notes
-----
This migration enables PostGIS and btree_gist. PostGIS must be installed
on the local Postgres 16 instance (EDB build) via Application Stack Builder
before running. Until then `alembic upgrade head` will fail loudly here,
which is intentional.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


# Single shared Enum instances — column references reuse them, so SQLAlchemy
# emits CREATE TYPE exactly once at the first create_table that needs them.
territory_kind = sa.Enum(
    "settlement", "volost", "uezd", "gubernia", "region",
    "country", "subdivision", "port", "station", "border_crossing",
    name="territory_kind",
)
empire = sa.Enum(
    "russian_empire", "austro_hungarian", "other",
    name="empire",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    op.create_table(
        "territories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", territory_kind, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("name_local", sa.String(255)),
        sa.Column(
            "parent_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("empire", empire, nullable=True, index=True),
        sa.Column("valid_from", sa.Date),
        sa.Column("valid_to", sa.Date),
        sa.Column(
            "geom",
            Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        ),
        sa.Column("is_umbrella_region", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_territories_kind_name", "territories", ["kind", "name"])

    op.create_table(
        "territory_aliases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "territory_id",
            sa.Integer,
            sa.ForeignKey("territories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("alias", sa.String(255), nullable=False, index=True),
        sa.Column("language", sa.String(16)),
        sa.Column("valid_from", sa.Date),
        sa.Column("valid_to", sa.Date),
        sa.UniqueConstraint("territory_id", "alias", "language", name="uq_alias_territory_lang"),
    )

    op.create_table(
        "periods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_from", sa.Date, nullable=False),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("description", sa.Text),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("short_title", sa.String(255), nullable=False, index=True),
        sa.Column("citation", sa.Text, nullable=False),
        sa.Column("kind", sa.String(64)),
        sa.Column("author", sa.String(255)),
        sa.Column("year", sa.Integer),
        sa.Column("url", sa.String(1024)),
        sa.Column("accessed_on", sa.Date),
        sa.Column("notes", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("sources")
    op.drop_table("periods")
    op.drop_table("territory_aliases")
    op.drop_index("ix_territories_kind_name", table_name="territories")
    op.drop_table("territories")
    empire.drop(op.get_bind(), checkfirst=True)
    territory_kind.drop(op.get_bind(), checkfirst=True)
