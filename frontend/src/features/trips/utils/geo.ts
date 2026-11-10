import type { Coord } from '@/integrations/rpc/api.gen'

/** Mean Earth radius, as backend `common/geo.py` uses. */
const EARTH_RADIUS_M = 6_371_008.8

const rad = (deg: number) => (deg * Math.PI) / 180

/** Great-circle distance in metres between two `[lon, lat]` points. */
export function haversineM(a: Coord, b: Coord): number {
  const [lon1, lat1] = a
  const [lon2, lat2] = b
  const dLat = rad(lat2 - lat1)
  const dLon = rad(lon2 - lon1)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Distance from the start to each vertex; the first entry is 0. */
export function cumulativeM(coords: readonly Coord[]): number[] {
  const out = [0]
  for (let i = 1; i < coords.length; i++) {
    out.push(out[i - 1]! + haversineM(coords[i - 1]!, coords[i]!))
  }
  return out
}

/**
 * The point `distanceM` along the line, clamped to its ends. Interpolates
 * linearly in lon/lat between vertices, which is exact enough at road scale.
 */
export function pointAlong(
  coords: readonly Coord[],
  cumulative: readonly number[],
  distanceM: number,
): Coord {
  if (coords.length === 0) throw new Error('pointAlong needs a non-empty line')
  if (distanceM <= 0 || coords.length === 1) return coords[0]!
  const total = cumulative[cumulative.length - 1]!
  if (distanceM >= total) return coords[coords.length - 1]!

  // The first vertex at or beyond the distance; the point lies just before it.
  let lo = 1
  let hi = cumulative.length - 1
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (cumulative[mid]! < distanceM) lo = mid + 1
    else hi = mid
  }
  const start = cumulative[lo - 1]!
  const span = cumulative[lo]! - start
  const t = span === 0 ? 0 : (distanceM - start) / span
  const [x1, y1] = coords[lo - 1]!
  const [x2, y2] = coords[lo]!
  return [x1 + (x2 - x1) * t, y1 + (y2 - y1) * t]
}

/** `[[west, south], [east, north]]` around every point, or null for none. */
export function boundsOf(
  coords: Iterable<Coord>,
): [[number, number], [number, number]] | null {
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity
  for (const [lon, lat] of coords) {
    west = Math.min(west, lon)
    east = Math.max(east, lon)
    south = Math.min(south, lat)
    north = Math.max(north, lat)
  }
  if (west === Infinity) return null
  return [
    [west, south],
    [east, north],
  ]
}
