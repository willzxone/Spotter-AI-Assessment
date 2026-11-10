"""Place search for the origin/destination pickers."""

from __future__ import annotations

import hashlib

from django.core.cache.backends.base import BaseCache

from core.errors import service_disabled
from modules.geocoding.adapters import GeocodingAdapter
from modules.geocoding.constants import SEARCH_CACHE_TTL_S
from modules.geocoding.dto import Place

_adapter: GeocodingAdapter | None = None
_cache: BaseCache | None = None


def configure(adapter: GeocodingAdapter, cache: BaseCache) -> None:
    global _adapter, _cache
    _adapter, _cache = adapter, cache


def search(query: str, limit: int) -> list[Place]:
    if _adapter is None or _cache is None:
        raise service_disabled("geocoding")
    normalized = " ".join(query.casefold().split())
    digest = hashlib.sha256(f"{normalized}|{limit}".encode()).hexdigest()[:32]
    key = f"geocoding:v1:{_adapter.source}:{digest}"
    cached = _cache.get(key)
    if cached is not None:
        return [Place.model_validate(item) for item in cached]
    places = _adapter.search(normalized, limit)
    # Store plain dicts: pydantic instances pickle fine, but dicts survive a class change on deploy.
    _cache.set(key, [place.model_dump() for place in places], SEARCH_CACHE_TTL_S)
    return places
