from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CountMethod = Literal["exact", "estimate", "range", "unknown"]
DatePrecision = Literal["day", "month", "year", "decade", "period", "unknown"]
MigrationVector = Literal[
    "transatlantic", "european", "intra_imperial_east",
    "intra_imperial_other", "internal",
]
TransportMode = Literal["land", "rail", "river", "sea", "mixed", "unknown"]
PrecisionLevel = Literal[
    "point", "settlement", "volost", "uezd", "gubernia",
    "region", "country", "vague",
]


class FlowSourceLink(BaseModel):
    source_id: int
    note: str | None = None


class FlowCreate(BaseModel):
    origin_territory_id: int
    destination_territory_id: int

    temporal_label_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    date_precision: DatePrecision = "unknown"

    count: int | None = Field(default=None, ge=0)
    count_lower: int | None = Field(default=None, ge=0)
    count_upper: int | None = Field(default=None, ge=0)
    count_method: CountMethod = "unknown"

    vector: MigrationVector
    transport_mode: TransportMode = "unknown"
    origin_precision: PrecisionLevel
    destination_precision: PrecisionLevel = "country"

    notes: str | None = None
    sources: list[FlowSourceLink] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_count_consistency(self):
        # Academic-integrity rule: count fields must match count_method.
        if self.count_method == "exact" and self.count is None:
            raise ValueError("count_method=exact requires `count`")
        if self.count_method == "range":
            if self.count_lower is None or self.count_upper is None:
                raise ValueError("count_method=range requires count_lower and count_upper")
            if self.count_lower > self.count_upper:
                raise ValueError("count_lower must be <= count_upper")
        if self.count_method == "unknown" and (
            self.count is not None or self.count_lower is not None or self.count_upper is not None
        ):
            raise ValueError(
                "count_method=unknown means we don't know — leave count fields blank"
            )
        return self


class FlowUpdate(BaseModel):
    """All fields optional; only provided ones are patched."""
    origin_territory_id: int | None = None
    destination_territory_id: int | None = None
    temporal_label_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    date_precision: DatePrecision | None = None
    count: int | None = None
    count_lower: int | None = None
    count_upper: int | None = None
    count_method: CountMethod | None = None
    vector: MigrationVector | None = None
    transport_mode: TransportMode | None = None
    origin_precision: PrecisionLevel | None = None
    destination_precision: PrecisionLevel | None = None
    notes: str | None = None
    provisional: bool | None = None
    sources: list[FlowSourceLink] | None = None  # if provided, replaces existing


class FlowSourceOut(BaseModel):
    source_id: int
    short_title: str
    note: str | None = None


class FlowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origin_territory_id: int
    origin_name: str | None = None
    destination_territory_id: int
    destination_name: str | None = None
    temporal_label_id: int | None
    temporal_label: str | None = None
    date_from: date | None
    date_to: date | None
    date_precision: str
    count: int | None
    count_lower: int | None
    count_upper: int | None
    count_method: str
    vector: str
    transport_mode: str
    origin_precision: str
    destination_precision: str
    provisional: bool
    notes: str | None
    sources: list[FlowSourceOut] = []
    created_at: datetime
    updated_at: datetime
