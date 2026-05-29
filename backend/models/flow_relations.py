"""Declared relationships between migration flows (Group E core).

A flow_relation is the user's analytical statement that two atomic flow
claims relate — one contains the other, they're the same movement, they're
disjoint, or they overlap by an unknown amount. The aggregation resolver uses
these to avoid double-counting in statistics. The program suggests candidates
(territory hierarchy + period overlap + same vector) but only persists a
relation once the user confirms it.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .enums import RelationKind, enum_values


class FlowRelation(Base):
    __tablename__ = "flow_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Directed: meaning is "from_flow {kind} to_flow". For CONTAINS, from_flow
    # is the larger/parent flow. The other kinds are conceptually symmetric.
    from_flow_id: Mapped[int] = mapped_column(
        ForeignKey("migration_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_flow_id: Mapped[int] = mapped_column(
        ForeignKey("migration_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[RelationKind] = mapped_column(
        Enum(RelationKind, name="relation_kind", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("from_flow_id", "to_flow_id", "kind", name="uq_flow_relation"),
        CheckConstraint("from_flow_id <> to_flow_id", name="ck_flow_relation_no_self"),
    )
