from django.http import HttpRequest

from core.rpc import Procedures
from modules.geocoding import service
from modules.geocoding.dto import SearchInput, SearchOutput

procedures = Procedures("geocoding")


@procedures.throttled(
    "search",
    output=SearchOutput,
    summary="Search places by name for the origin/destination pickers",
    per_minute=90,
)
def search(request: HttpRequest, payload: SearchInput) -> SearchOutput:
    return SearchOutput(places=service.search(payload.query, payload.limit))
