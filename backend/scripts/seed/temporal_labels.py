"""Seed the temporal_labels catalogue.

Auto-generates:
- decades 1800-2010 ("1880-і", year_from=1880, year_to=1889)
- quarter centuries XVIII-XX (8 entries × 3 = 24)
- half centuries XVIII-XX (2 × 3 = 6)
- centuries XVIII / XIX / XX
- era labels: Поч., Сер., Кін. XIX / XX (fuzzy human-named ranges)
- named research periods (formerly in `periods` table — already migrated;
  seeder ensures presence if a fresh DB skips the data migration path)

Idempotent on `slug`.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from backend.models.enums import TemporalLabelKind
from backend.models.temporal import TemporalLabel

from ._common import logger, session_scope


def _roman(century: int) -> str:
    return {18: "XVIII", 19: "XIX", 20: "XX", 21: "XXI"}[century]


def _build_specs() -> list[dict]:
    specs: list[dict] = []

    # Decades 1800-2010
    for start in range(1800, 2020, 10):
        end = start + 9
        specs.append({
            "slug": f"decade-{start}",
            "label": f"{start}-і",
            "kind": TemporalLabelKind.DECADE,
            "year_from": start,
            "year_to": end,
        })

    for century in (18, 19, 20):
        c0 = (century - 1) * 100  # year 1800 for XIX

        # Full century
        specs.append({
            "slug": f"century-{century}",
            "label": f"{_roman(century)} ст.",
            "kind": TemporalLabelKind.CENTURY,
            "year_from": c0,
            "year_to": c0 + 99,
        })

        # Halves
        specs.append({
            "slug": f"half-{century}-1",
            "label": f"Перша половина {_roman(century)} ст.",
            "kind": TemporalLabelKind.HALF_CENTURY,
            "year_from": c0,
            "year_to": c0 + 49,
        })
        specs.append({
            "slug": f"half-{century}-2",
            "label": f"Друга половина {_roman(century)} ст.",
            "kind": TemporalLabelKind.HALF_CENTURY,
            "year_from": c0 + 50,
            "year_to": c0 + 99,
        })

        # Quarters
        for q in (1, 2, 3, 4):
            qs = c0 + (q - 1) * 25
            specs.append({
                "slug": f"quarter-{century}-{q}",
                "label": f"{q}-та чверть {_roman(century)} ст.",
                "kind": TemporalLabelKind.QUARTER_CENTURY,
                "year_from": qs,
                "year_to": qs + 24,
            })

        # Fuzzy era labels — broader, deliberately overlapping with quarters/halves
        specs.append({
            "slug": f"era-pochatok-{century}",
            "label": f"Початок {_roman(century)} ст.",
            "kind": TemporalLabelKind.ERA_LABEL,
            "year_from": c0,
            "year_to": c0 + 19,
            "description": "Перші два десятиліття століття",
        })
        specs.append({
            "slug": f"era-seredyna-{century}",
            "label": f"Середина {_roman(century)} ст.",
            "kind": TemporalLabelKind.ERA_LABEL,
            "year_from": c0 + 30,
            "year_to": c0 + 70,
        })
        specs.append({
            "slug": f"era-kinets-{century}",
            "label": f"Кінець {_roman(century)} ст.",
            "kind": TemporalLabelKind.ERA_LABEL,
            "year_from": c0 + 80,
            "year_to": c0 + 99,
            "description": "Останні два десятиліття століття",
        })

    # Named research periods — replicated here so a fresh DB seed without
    # running the 0004 data migration still has them. Migration 0004 also
    # inserts these on existing installs.
    specs.extend([
        {
            "slug": "first-wave",
            "label": "Перша хвиля переселення (1880–1914)",
            "kind": TemporalLabelKind.NAMED_PERIOD,
            "year_from": 1880, "year_to": 1914,
            "description": "Масова трудова й селянська еміграція до США, Канади, "
                            "Бразилії, Аргентини; внутрішньоімперські переселення до Сибіру й Далекого Сходу.",
        },
        {
            "slug": "wwi-civil-war",
            "label": "Перша світова та національно-визвольні змагання (1914–1921)",
            "kind": TemporalLabelKind.NAMED_PERIOD,
            "year_from": 1914, "year_to": 1921,
        },
        {
            "slug": "interwar",
            "label": "Міжвоєнний період (1921–1939)",
            "kind": TemporalLabelKind.NAMED_PERIOD,
            "year_from": 1921, "year_to": 1939,
            "description": "Друга хвиля політичної еміграції; квотні обмеження США (1924).",
        },
        {
            "slug": "wwii",
            "label": "Друга світова війна (1939–1945)",
            "kind": TemporalLabelKind.NAMED_PERIOD,
            "year_from": 1939, "year_to": 1945,
        },
        {
            "slug": "postwar-dp",
            "label": "Повоєнна еміграція DP (1945–1955)",
            "kind": TemporalLabelKind.NAMED_PERIOD,
            "year_from": 1945, "year_to": 1955,
        },
    ])

    return specs


def run() -> None:
    with session_scope() as db:
        for spec in _build_specs():
            exists = db.execute(
                select(TemporalLabel).where(TemporalLabel.slug == spec["slug"])
            ).scalar_one_or_none()
            if exists:
                continue
            db.add(TemporalLabel(**spec))
            logger.info("seeded temporal label %s (%s)", spec["slug"], spec["kind"].value)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
