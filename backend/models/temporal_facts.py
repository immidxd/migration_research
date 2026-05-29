"""Time-varying attributes of a territory, and territorial stock facts.

Two tables, both anchored to a single Territory row (which keeps ONE geometry
and ONE id, so flows/events/stats never fragment across "versions"):

- TerritoryPeriod: the political status / display name / sovereign of a
  territory during a [year_from, year_to] window. Lets one Hawaii row read as
  "Королівство Гаваї" before annexation and "Гаваї (США)" after, without
  duplicating geometry.

- TerritoryStat: a stock/snapshot fact about a territory at a point in time
  ("10,000 Ukrainians in Canada as of 1908"). NOT a flow — it measures a state,
  not movement. Carries its own sources and the same count-method discipline as
  flows; sourceless rows are provisional.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import CountMethod, StatKind, enum_values


class TerritoryPeriod(Base):
    """Period-scoped attributes of a territory (status / name / sovereign)."""

    __tablename__ = "territory_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Inclusive year window this attribute-set holds for.
    year_from: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Political status during the period — free text so it fits any era
    # ("Королівство", "Територія США", "Штат США", "Коронний край" …).
    status: Mapped[str | None] = mapped_column(String(255))
    # Display name overrides for the period (fall back to Territory.name* if null).
    name: Mapped[str | None] = mapped_column(String(255))
    name_local: Mapped[str | None] = mapped_column(String(255))
    # The sovereign / parent polity during the period (e.g. USA after 1898).
    sovereign_id: Mapped[int | None] = mapped_column(
        ForeignKey("territories.id", ondelete="SET NULL"), index=True
    )

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sources = relationship("Source", secondary="territory_period_sources", lazy="selectin")


class TerritoryStat(Base):
    """A territorial stock / snapshot fact (e.g. diaspora population as of a year)."""

    __tablename__ = "territory_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    territory_id: Mapped[int] = mapped_column(
        ForeignKey("territories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    stat_kind: Mapped[StatKind] = mapped_column(
        Enum(StatKind, name="stat_kind", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    # For DIASPORA_STOCK: the origin/ethnic group the count refers to
    # ("українці", "галичани"). Null for TOTAL_POPULATION.
    group_label: Mapped[str | None] = mapped_column(String(255))

    # "as of" year for a point-in-time stock; temporal_label_id for a named
    # period. At least one should be set.
    as_of_year: Mapped[int | None] = mapped_column(Integer, index=True)
    temporal_label_id: Mapped[int | None] = mapped_column(
        ForeignKey("temporal_labels.id", ondelete="SET NULL"), index=True
    )

    count: Mapped[int | None] = mapped_column(Integer)
    count_lower: Mapped[int | None] = mapped_column(Integer)
    count_upper: Mapped[int | None] = mapped_column(Integer)
    count_method: Mapped[CountMethod] = mapped_column(
        Enum(CountMethod, name="count_method", values_callable=enum_values),
        nullable=False,
        server_default=CountMethod.UNKNOWN.value,
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

    sources = relationship("Source", secondary="territory_stat_sources", lazy="selectin")
