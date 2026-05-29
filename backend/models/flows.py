"""Migration flows and events — the core "fact" tables.

Academic-integrity rules baked in:
- Every flow/event carries an explicit `precision_level` (REGION → POINT).
  A flow bound to "Pravoberezhzhia" stays bound to that umbrella region and
  is NEVER silently split across child gubernias by the system.
- A flow with no source(s) attached must have `provisional=True`. The UI
  surfaces provisional records visibly and excludes them from aggregations
  alongside cited ones.
- If two sources disagree on numbers for the same flow, store BOTH as
  separate rows (each with its own source link), do not pick a winner.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    CountMethod,
    DatePrecision,
    MigrationVector,
    PrecisionLevel,
    ShareBaseKind,
    TransportMode,
    enum_values,
)


class MigrationFlow(Base):
    """Aggregated migration flow between two territories within a period.

    "Aggregated" means: a number of people moved from X to Y between dates A
    and B, per a specific source. One flow = one source's claim. Disagreeing
    sources are stored as separate flows.
    """

    __tablename__ = "migration_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    origin_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    temporal_label_id: Mapped[int | None] = mapped_column(
        ForeignKey("temporal_labels.id", ondelete="SET NULL"), index=True
    )
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    date_precision: Mapped[DatePrecision] = mapped_column(
        Enum(DatePrecision, name="date_precision", values_callable=enum_values),
        nullable=False,
        server_default=DatePrecision.UNKNOWN.value,
    )

    # Counts: either a firm `count`, or a `[count_lower, count_upper]` range,
    # or all-null with method=UNKNOWN. We do not invent numbers.
    count: Mapped[int | None] = mapped_column(Integer)
    count_lower: Mapped[int | None] = mapped_column(Integer)
    count_upper: Mapped[int | None] = mapped_column(Integer)
    count_method: Mapped[CountMethod] = mapped_column(
        Enum(CountMethod, name="count_method", values_callable=enum_values),
        nullable=False,
        server_default=CountMethod.UNKNOWN.value,
    )

    # SHARE quantity: a percentage of an explicit base. Only meaningful when
    # count_method=share. The resolver multiplies share_pct by the base's
    # resolved magnitude. A share with no base is rejected at the API layer.
    share_pct: Mapped[float | None] = mapped_column(Float)
    share_pct_lower: Mapped[float | None] = mapped_column(Float)
    share_pct_upper: Mapped[float | None] = mapped_column(Float)
    share_base_kind: Mapped[ShareBaseKind | None] = mapped_column(
        Enum(ShareBaseKind, name="share_base_kind", values_callable=enum_values)
    )
    share_base_flow_id: Mapped[int | None] = mapped_column(
        ForeignKey("migration_flows.id", ondelete="SET NULL"), index=True
    )
    share_base_territory_id: Mapped[int | None] = mapped_column(
        ForeignKey("territories.id", ondelete="SET NULL"), index=True
    )

    vector: Mapped[MigrationVector] = mapped_column(
        Enum(MigrationVector, name="migration_vector", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    transport_mode: Mapped[TransportMode] = mapped_column(
        Enum(TransportMode, name="transport_mode", values_callable=enum_values),
        nullable=False,
        server_default=TransportMode.UNKNOWN.value,
    )

    # Precision of the ORIGIN — drives map rendering (point vs polygon).
    origin_precision: Mapped[PrecisionLevel] = mapped_column(
        Enum(PrecisionLevel, name="precision_level", values_callable=enum_values),
        nullable=False,
    )
    # Precision of the DESTINATION (often coarser than origin in sources).
    destination_precision: Mapped[PrecisionLevel] = mapped_column(
        Enum(PrecisionLevel, name="precision_level", values_callable=enum_values),
        nullable=False,
        server_default=PrecisionLevel.COUNTRY.value,
    )

    # Provenance flags.
    provisional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sources = relationship("Source", secondary="flow_sources", lazy="selectin")
    waypoints = relationship(
        "FlowWaypoint",
        cascade="all, delete-orphan",
        order_by="FlowWaypoint.sequence_no",
        lazy="selectin",
    )


class FlowWaypoint(Base):
    """An ordered transit / transshipment point a flow passed through.

    Lets a flow record its real multi-hop path (Kyiv → Libau → US; the
    Chelyabinsk resettlement point) without inventing intermediate flows.
    The path is origin → waypoint[0] → … → destination. Branching at a
    waypoint is modelled as separate flows departing that point, linked to the
    parent via flow_relations (contains) — not here.
    """

    __tablename__ = "flow_waypoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flow_id: Mapped[int] = mapped_column(
        ForeignKey("migration_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("flow_id", "sequence_no", name="uq_flow_waypoint_order"),
    )


class MigrationEvent(Base):
    """A single migration event — a family, party, ship's manifest entry, etc.

    Finer-grained than a flow. May reference a route the event followed.
    """

    __tablename__ = "migration_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str | None] = mapped_column(String(255))  # family name, group name

    origin_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    route_id: Mapped[int | None] = mapped_column(
        ForeignKey("routes.id", ondelete="SET NULL"), index=True
    )

    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    date_precision: Mapped[DatePrecision] = mapped_column(
        Enum(DatePrecision, name="date_precision", values_callable=enum_values),
        nullable=False,
        server_default=DatePrecision.UNKNOWN.value,
    )

    people_count: Mapped[int | None] = mapped_column(Integer)
    vector: Mapped[MigrationVector] = mapped_column(
        Enum(MigrationVector, name="migration_vector", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    transport_mode: Mapped[TransportMode] = mapped_column(
        Enum(TransportMode, name="transport_mode", values_callable=enum_values),
        nullable=False,
        server_default=TransportMode.UNKNOWN.value,
    )
    origin_precision: Mapped[PrecisionLevel] = mapped_column(
        Enum(PrecisionLevel, name="precision_level", values_callable=enum_values),
        nullable=False,
    )
    destination_precision: Mapped[PrecisionLevel] = mapped_column(
        Enum(PrecisionLevel, name="precision_level", values_callable=enum_values),
        nullable=False,
        server_default=PrecisionLevel.COUNTRY.value,
    )

    provisional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sources = relationship("Source", secondary="event_sources", lazy="selectin")
