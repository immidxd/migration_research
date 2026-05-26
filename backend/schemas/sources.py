from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    short_title: str = Field(min_length=1, max_length=255)
    citation: str = Field(min_length=1)
    kind: str | None = Field(default=None, max_length=64)
    author: str | None = Field(default=None, max_length=255)
    year: int | None = None
    url: str | None = Field(default=None, max_length=1024)
    accessed_on: date | None = None
    notes: str | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_title: str
    citation: str
    kind: str | None
    author: str | None
    year: int | None
    url: str | None
    accessed_on: date | None
    notes: str | None = None
