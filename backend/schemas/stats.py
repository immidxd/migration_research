from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CountMethod = Literal["exact", "estimate", "range", "unknown"]
StatKind = Literal["diaspora_stock", "total_population", "immigrant_arrivals", "other"]


class StatSourceLink(BaseModel):
    source_id: int
    note: str | None = None


class _StatCountMixin(BaseModel):
    @model_validator(mode="after")
    def _check_count(self):
        if self.count_method == "exact" and self.count is None:
            raise ValueError("count_method=exact requires `count`")
        if self.count_method == "range" and (self.count_lower is None or self.count_upper is None):
            raise ValueError("count_method=range requires count_lower and count_upper")
        if self.count_method == "range" and self.count_lower > self.count_upper:
            raise ValueError("count_lower must be <= count_upper")
        return self


class StatCreate(_StatCountMixin):
    territory_id: int
    stat_kind: StatKind
    group_label: str | None = None

    as_of_year: int | None = None
    temporal_label_id: int | None = None

    count: int | None = Field(default=None, ge=0)
    count_lower: int | None = Field(default=None, ge=0)
    count_upper: int | None = Field(default=None, ge=0)
    count_method: CountMethod = "unknown"

    notes: str | None = None
    sources: list[StatSourceLink] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_when(self):
        if self.as_of_year is None and self.temporal_label_id is None:
            raise ValueError("set either as_of_year or temporal_label_id")
        return self


class StatUpdate(_StatCountMixin):
    territory_id: int | None = None
    stat_kind: StatKind | None = None
    group_label: str | None = None
    as_of_year: int | None = None
    temporal_label_id: int | None = None
    count: int | None = None
    count_lower: int | None = None
    count_upper: int | None = None
    count_method: CountMethod = "unknown"
    provisional: bool | None = None
    notes: str | None = None
    sources: list[StatSourceLink] | None = None


class StatSourceOut(BaseModel):
    source_id: int
    short_title: str
    note: str | None = None


class StatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    territory_id: int
    territory_name: str | None = None
    stat_kind: str
    group_label: str | None
    as_of_year: int | None
    temporal_label_id: int | None
    temporal_label: str | None = None
    count: int | None
    count_lower: int | None
    count_upper: int | None
    count_method: str
    provisional: bool
    notes: str | None
    sources: list[StatSourceOut] = []
    created_at: datetime
    updated_at: datetime


class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    territory_id: int
    year_from: int
    year_to: int
    status: str | None
    name: str | None
    name_local: str | None
    sovereign_id: int | None
    notes: str | None
