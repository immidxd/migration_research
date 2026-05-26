"""Shared helpers for seeders.

Idempotency contract: every seeder must be safe to re-run. Match on
`Territory.code` (preferred) or `Source.short_title` (for Sources).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import SessionLocal
from backend.models.sources import Source


logger = logging.getLogger("migrations.seed")


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_or_create_source(db: Session, short_title: str, **fields) -> Source:
    existing = db.execute(
        select(Source).where(Source.short_title == short_title)
    ).scalar_one_or_none()
    if existing:
        return existing
    src = Source(short_title=short_title, **fields)
    db.add(src)
    db.flush()  # populate id
    return src
