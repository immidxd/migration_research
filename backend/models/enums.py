from __future__ import annotations

import enum


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
