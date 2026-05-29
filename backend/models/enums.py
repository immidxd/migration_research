from __future__ import annotations

import enum


def enum_values(e: type[enum.Enum]) -> list[str]:
    """For sa.Enum(..., values_callable=enum_values) — sends string values
    (e.g. 'region') to Postgres instead of Python enum names ('REGION')."""
    return [m.value for m in e]


class PrecisionLevel(str, enum.Enum):
    """How geographically precise a record is.

    Academic rule: a record bound at REGION level (e.g. "Pravoberezhzhia")
    must never be silently split across child gubernias. The level is part
    of the data, not a UI hint.
    """

    POINT = "point"
    SETTLEMENT = "settlement"
    VOLOST = "volost"
    UEZD = "uezd"
    GUBERNIA = "gubernia"
    REGION = "region"
    COUNTRY = "country"
    VAGUE = "vague"


class TerritoryKind(str, enum.Enum):
    SETTLEMENT = "settlement"
    VOLOST = "volost"
    UEZD = "uezd"
    GUBERNIA = "gubernia"
    REGION = "region"  # umbrella historical region (Pravoberezhzhia, Slobozhanshchyna, ...)
    COUNTRY = "country"
    SUBDIVISION = "subdivision"  # state / province / land
    PORT = "port"
    STATION = "station"
    BORDER_CROSSING = "border_crossing"


class MigrationVector(str, enum.Enum):
    """High-level migration direction — drives the sidebar vector toggles."""

    TRANSATLANTIC = "transatlantic"
    EUROPEAN = "european"
    INTRA_IMPERIAL_EAST = "intra_imperial_east"  # Volga, Urals, Siberia, Far East
    INTRA_IMPERIAL_OTHER = "intra_imperial_other"
    INTERNAL = "internal"  # within Ukrainian lands


class Empire(str, enum.Enum):
    RUSSIAN = "russian_empire"
    AUSTRO_HUNGARIAN = "austro_hungarian"
    OTHER = "other"


class TransportMode(str, enum.Enum):
    LAND = "land"
    RAIL = "rail"
    RIVER = "river"
    SEA = "sea"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class DatePrecision(str, enum.Enum):
    """How precisely the date(s) on a fact are known."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    DECADE = "decade"
    PERIOD = "period"  # only named-period precision (no raw dates)
    UNKNOWN = "unknown"


class TemporalLabelKind(str, enum.Enum):
    """Granularity of a temporal label.

    Containment hierarchy (broader → narrower):
        century > half_century > quarter_century > decade > year
    Plus orthogonal:
        era_label   — fuzzy human label ("Кінець XIX ст.", "Поч. XX ст.")
        named_period — researcher-defined named period (first-wave, interwar…)
    All carry a canonical [year_from, year_to] range, so filtering reduces to
    interval overlap regardless of which kind a fact was tagged with.
    """

    YEAR = "year"
    DECADE = "decade"
    QUARTER_CENTURY = "quarter_century"
    HALF_CENTURY = "half_century"
    CENTURY = "century"
    ERA_LABEL = "era_label"
    NAMED_PERIOD = "named_period"


class CountMethod(str, enum.Enum):
    """How the people-count on a flow/event was derived from the source."""

    EXACT = "exact"          # source gives a single firm number
    ESTIMATE = "estimate"    # source or scholar gives an estimate
    RANGE = "range"          # only a lower/upper range is known
    UNKNOWN = "unknown"      # no count, or unrecoverable


class RelationKind(str, enum.Enum):
    """How two flows relate, for overlap-aware aggregation.

    Directed edge from_flow → to_flow:
      CONTAINS  — from_flow contains to_flow (to_flow is a part of from_flow);
                  the only asymmetric kind. The aggregator subtracts contained
                  children when summing with their parent.
      EQUALS    — the two flows describe the same movement (e.g. two sources for
                  the same claim); keep one when aggregating. Symmetric.
      DISJOINT  — confirmed non-overlapping; safe to add together. Symmetric.
      OVERLAPS_UNKNOWN — they overlap but the extent is unknown; the aggregator
                  surfaces a RANGE instead of a false precise sum. Symmetric.

    Relationships are the USER's analytical declarations (confirmed). The
    program only suggests candidates; it never stores a relation unconfirmed.
    """

    CONTAINS = "contains"
    EQUALS = "equals"
    DISJOINT = "disjoint"
    OVERLAPS_UNKNOWN = "overlaps_unknown"


class StatKind(str, enum.Enum):
    """Kind of a territorial stock/snapshot fact (territory_stats).

    A "stock" is a state-at-a-point-in-time, NOT a flow: e.g. "10,000
    Ukrainians counted in Canada as of 1908". Distinct from migration_flows,
    which measure movement between two places over a period.
    """

    DIASPORA_STOCK = "diaspora_stock"        # people of an origin group present in a place
    TOTAL_POPULATION = "total_population"     # total population of the territory
    IMMIGRANT_ARRIVALS = "immigrant_arrivals"  # arrivals counted in a year (annual inflow)
    OTHER = "other"
