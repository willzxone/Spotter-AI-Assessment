"""Geocoding adapters: off, simulated (offline gazetteer) and live (Photon / OpenStreetMap)."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from core.errors import service_disabled, upstream_unavailable
from modules.geocoding.constants import GAZETTEER
from modules.geocoding.dto import Place


class GeocodingAdapter(Protocol):
    source: str

    def search(self, query: str, limit: int) -> list[Place]: ...


class OffGeocoder:
    source = "off"

    def search(self, query: str, limit: int) -> list[Place]:
        raise service_disabled("geocoding")


class SimulatedGeocoder:
    """Matches a fixed list of US freight hubs. Deterministic; no network."""

    source = "simulated"

    def search(self, query: str, limit: int) -> list[Place]:
        needle = query.casefold()
        starts = [p for p in GAZETTEER if p.name.casefold().startswith(needle)]
        contains = [p for p in GAZETTEER if needle in p.label.casefold() and p not in starts]
        return (starts + contains)[:limit]


class PhotonGeocoder:
    """Photon (https://photon.komoot.io): OSM-based search-as-you-type, no key required."""

    source = "photon"

    def __init__(self, http: httpx.Client, base_url: str) -> None:
        self._http = http
        self._url = base_url.rstrip("/") + "/api"

    def search(self, query: str, limit: int) -> list[Place]:
        try:
            response = self._http.get(self._url, params={"q": query, "limit": limit, "lang": "en"})
        except httpx.HTTPError as exc:
            raise upstream_unavailable("geocoding", type(exc).__name__) from exc
        if response.status_code == 429:
            raise upstream_unavailable("geocoding", "the provider is rate limiting us")
        if response.status_code >= 400:
            raise upstream_unavailable("geocoding", f"HTTP {response.status_code}")
        try:
            features = response.json().get("features", [])
        except ValueError as exc:
            raise upstream_unavailable("geocoding", "unreadable response") from exc
        places: list[Place] = []
        seen: set[str] = set()
        for feature in features:
            place = _to_place(feature)
            if place is not None and place.label not in seen:
                seen.add(place.label)
                places.append(place)
        return places


def _to_place(feature: dict[str, Any]) -> Place | None:
    try:
        lon, lat = feature["geometry"]["coordinates"][:2]
        props = feature.get("properties", {})
    except (KeyError, TypeError, ValueError):
        return None
    name = props.get("name") or props.get("street") or props.get("city")
    if not name:
        return None
    if props.get("housenumber") and props.get("street"):
        name = f"{props['housenumber']} {props['street']}"
    parts: list[str] = []
    for part in (name, props.get("city"), props.get("state"), props.get("country")):
        if part and part not in parts:
            parts.append(part)
    osm_id = f"{props.get('osm_type', '')}{props.get('osm_id', '')}" or f"{lat:.5f},{lon:.5f}"
    return Place(
        id=osm_id,
        name=str(name),
        label=", ".join(parts),
        lat=float(lat),
        lon=float(lon),
        kind=props.get("type") or props.get("osm_value"),
    )
