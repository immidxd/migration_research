from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Source(Base):
    """Archival or bibliographic source backing a record.

    Every fact in the system must point at a Source. The citation field is
    free text on purpose — archive fond/opys/sprava/arkush conventions vary
    and we don't want to lose nuance.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    short_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str | None] = mapped_column(String(64))  # archive / monograph / article / dataset
    author: Mapped[str | None] = mapped_column(String(255))
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(1024))
    accessed_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
