"""Base class for every API input and output shape."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    """camelCase on the wire, snake_case in Python.

    `extra="forbid"` makes inputs strict: an unknown key is a client bug, so it is
    rejected instead of silently ignored. Models are frozen so a DTO handed to
    another module cannot be mutated behind the owner's back.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        extra="forbid",
        frozen=True,
    )
