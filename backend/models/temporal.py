"""Unified temporal labels — supersedes the old `periods` table.

Any classification of "when" a fact happened lives here:
year, decade, quarter/half/full century, fuzzy era label
("Кінець XIX ст.", "Поч. XX ст."), or a named research period.

Every label carries a canonical [year_from, year_to] inclusive range, so
filtering reduces to interval overlap regardless of the label's kind. This
implements the user's rule: "broader contains narrower, but not vice versa"
naturally — selecting label X shows facts whose canonical range falls
inside X's range (strict containment), and optionally facts that merely
overlap (broader-scope match, surfaced dimmed).
"""
from __future__ import annotations

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .enums import TemporalLabelKind, enum_values


class TemporalLabel(Base):
    __tablename__ = "temporal_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[TemporalLabelKind] = mapped_column(
        Enum(TemporalLabelKind, name="temporal_label_kind", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    year_from: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
