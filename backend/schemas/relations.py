from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


RelationKind = Literal["contains", "equals", "disjoint", "overlaps_unknown"]


class RelationCreate(BaseModel):
    from_flow_id: int
    to_flow_id: int
    kind: RelationKind
    note: str | None = None

    @model_validator(mode="after")
    def _no_self(self):
        if self.from_flow_id == self.to_flow_id:
            raise ValueError("a flow cannot relate to itself")
        return self


class RelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_flow_id: int
    from_label: str | None = None
    to_flow_id: int
    to_label: str | None = None
    kind: str
    note: str | None
    created_at: datetime


class RelationCandidate(BaseModel):
    """A suggested (not yet stored) relation the user can confirm one-click."""

    other_flow_id: int
    other_label: str
    other_count: int | None = None
    other_period: str | None = None
    # Ready-to-POST proposal:
    from_flow_id: int
    to_flow_id: int
    kind: RelationKind
    reason: str
