"""Routes and route segments.

A Route is an ordered series of RouteSegments. Each segment carries its own
geometry (LINESTRING), transport mode, and date range — because a single
route can shift over time (a port closes, a railway opens).
"""
from __future__ import annotations

from datetime import date

from geoalchemy2 import Geometry
from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import MigrationVector, TransportMode, enum_values


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vector: Mapped[MigrationVector] = mapped_column(
        Enum(MigrationVector, name="migration_vector", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    segments = relationship(
        "RouteSegment",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteSegment.sequence_no",
    )
    sources = relationship("Source", secondary="route_sources", lazy="selectin")


class RouteSegment(Base):
    __tablename__ = "route_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)

    from_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    transport_mode: Mapped[TransportMode] = mapped_column(
        Enum(TransportMode, name="transport_mode", values_callable=enum_values),
        nullable=False,
    )
    geom: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True)
    )
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    route = relationship("Route", back_populates="segments")

    __table_args__ = (
        UniqueConstraint("route_id", "sequence_no", name="uq_route_segment_order"),
    )


class TransitPointProfile(Base):
    """Extra metadata on a Territory of kind PORT / STATION / BORDER_CROSSING.

    Kept as a side table (instead of swelling territories) so generic
    territorial queries stay simple. The Territory remains the canonical
    place row.
    """

    __tablename__ = "transit_point_profiles"

    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="CASCADE"), primary_key=True
    )
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)
    operator: Mapped[str | None] = mapped_column(String(255))  # shipping line, railway company
    notes: Mapped[str | None] = mapped_column(Text)
