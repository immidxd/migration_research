from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Period(Base):
    """Named research period (e.g. "First wave 1880-1914", "Interwar").

    Periods are *named labels* the researcher attaches to flows, separate
    from the raw date range on each fact. A flow can also carry only raw
    dates without belonging to any named period.
    """

    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
