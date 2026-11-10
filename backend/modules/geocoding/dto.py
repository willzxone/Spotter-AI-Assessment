from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from core.schema import ApiSchema


class Place(ApiSchema):
    id: str
    name: str
    # Full human label, e.g. "Joliet, Illinois, United States".
    label: str
    lat: float
    lon: float
    kind: str | None = None


class SearchInput(ApiSchema):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    limit: Annotated[int, Field(ge=1, le=10)] = 6


class SearchOutput(ApiSchema):
    places: list[Place]
