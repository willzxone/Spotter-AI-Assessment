"""Procedure builders — the only way a module exposes API surface.

Everything is RPC at `POST /rpc/<module>/<procedure>`; there is no REST surface.
A module creates one `Procedures` for itself and declares each procedure with an
access level. Today the app has no accounts, so the levels are:

    public     — anyone
    throttled  — public, plus a per-IP rate limit scoped to that one procedure

Input and output are pydantic models (`core.schema.ApiSchema`); Ninja validates
the input before the handler runs and serialises the output by alias (camelCase).

Router files must NOT use `from __future__ import annotations`: Ninja reads the
handler's parameter annotations at import time to build the input model.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from ninja import Router
from ninja.throttling import AnonRateThrottle

Handler = TypeVar("Handler", bound=Callable[..., Any])


class _ProcedureThrottle(AnonRateThrottle):
    """Per-IP limit whose history is keyed by procedure, so limits never share a bucket."""

    def __init__(self, scope: str, rate: str) -> None:
        self.scope = scope
        super().__init__(rate)


class Procedures:
    def __init__(self, module: str) -> None:
        self.module = module
        self.router = Router(tags=[module])

    def _operation(
        self,
        name: str,
        *,
        output: type[Any],
        summary: str,
        throttle: list[_ProcedureThrottle] | None = None,
    ) -> Callable[[Handler], Handler]:
        procedure_id = f"{self.module}.{name}"
        kwargs: dict[str, Any] = {}
        if throttle:
            kwargs["throttle"] = throttle
        return self.router.post(
            f"/{name}",
            response=output,
            by_alias=True,
            operation_id=procedure_id,
            summary=summary,
            url_name=procedure_id,
            **kwargs,
        )

    def public(self, name: str, *, output: type[Any], summary: str) -> Callable[[Handler], Handler]:
        return self._operation(name, output=output, summary=summary)

    def throttled(
        self, name: str, *, output: type[Any], summary: str, per_minute: int
    ) -> Callable[[Handler], Handler]:
        scope = f"{self.module}.{name}"
        return self._operation(
            name,
            output=output,
            summary=summary,
            throttle=[_ProcedureThrottle(scope, f"{per_minute}/m")],
        )
