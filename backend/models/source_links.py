"""Many-to-many link tables between fact entities and sources.

Per the project's sources-first rule (see project memory): every fact
should be citable by one or more sources, and bibliographic browsing
("show me everything from source X") should be cheap.

A separate link table per entity (rather than a polymorphic table) keeps
referential integrity strict.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class FlowSource(Base):
    __tablename__ = "flow_sources"
    flow_id: Mapped[int] = mapped_column(
        ForeignKey("migration_flows.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (PrimaryKeyConstraint("flow_id", "source_id"),)


class EventSource(Base):
    __tablename__ = "event_sources"
    event_id: Mapped[int] = mapped_column(
        ForeignKey("migration_events.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (PrimaryKeyConstraint("event_id", "source_id"),)


class RouteSource(Base):
    __tablename__ = "route_sources"
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (PrimaryKeyConstraint("route_id", "source_id"),)


class TerritorySource(Base):
    """Source-attestation of a territory's existence/extent (e.g. a historic map)."""

    __tablename__ = "territory_sources"
    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (PrimaryKeyConstraint("territory_id", "source_id"),)


class AliasSource(Base):
    """Source-attestation of a territory's alias being used at a given time."""

    __tablename__ = "alias_sources"
    alias_id: Mapped[int] = mapped_column(
        ForeignKey("territory_aliases.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (PrimaryKeyConstraint("alias_id", "source_id"),)
