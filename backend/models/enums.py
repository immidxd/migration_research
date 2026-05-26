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


class CountMethod(str, enum.Enum):
    """How the people-count on a flow/event was derived from the source."""

    EXACT = "exact"          # source gives a single firm number
    ESTIMATE = "estimate"    # source or scholar gives an estimate
    RANGE = "range"          # only a lower/upper range is known
    UNKNOWN = "unknown"      # no count, or unrecoverable
