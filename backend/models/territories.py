from __future__ import annotations

from datetime import date

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import Empire, TerritoryKind


class Territory(Base):
    """A historical administrative or geographic unit.

    Hierarchy via `parent_id`. Geometry stored in EPSG:4326 (WGS84).
    `valid_from` / `valid_to` describe the unit's period of existence —
    *not* a UI filter, but the actual historical lifespan of the entity.
    """

    __tablename__ = "territories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[TerritoryKind] = mapped_column(
        Enum(TerritoryKind, name="territory_kind"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_local: Mapped[str | None] = mapped_column(String(255))  # native-language name
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("territories.id", ondelete="SET NULL"), index=True
    )

    empire: Mapped[Empire | None] = mapped_column(
        Enum(Empire, name="empire"), nullable=True, index=True
    )

    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    # Polygon / multipolygon for areas; point for settlements/ports/stations.
    geom: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True)
    )

    # If this is an umbrella historical region (kind=REGION) used to anchor
    # records of vague origin like "Pravoberezhzhia".
    is_umbrella_region: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)

    parent = relationship("Territory", remote_side="Territory.id", backref="children")
    aliases = relationship(
        "TerritoryAlias", back_populates="territory", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_territories_kind_name", "kind", "name"),
    )


class TerritoryAlias(Base):
    """Alternative names by period and language.

    Example: Katerynoslav / Dnipropetrovsk / Sicheslav / Ekaterinoslav
    for the same Territory id, each with its own valid date range and language.
    """

    __tablename__ = "territory_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(16))  # ISO 639-1/2 code
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    territory = relationship("Territory", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("territory_id", "alias", "language", name="uq_alias_territory_lang"),
    )
