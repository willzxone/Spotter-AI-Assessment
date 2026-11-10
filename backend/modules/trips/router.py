from django.http import HttpRequest

from core.rpc import Procedures
from modules.trips import service
from modules.trips.dto import PlanInput, PlanOutput

procedures = Procedures("trips")


@procedures.throttled(
    "plan",
    output=PlanOutput,
    summary="Plan up to 3 routes, score weather risk at every checkpoint ETA and recommend one",
    per_minute=20,
)
def plan(request: HttpRequest, payload: PlanInput) -> PlanOutput:
    return service.plan(payload)
