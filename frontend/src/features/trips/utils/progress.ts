import type { Coord, HeatmapOut, RouteOut } from '@/integrations/rpc/api.gen'
import { cumulativeM, pointAlong } from './geo'

const HOUR_MS = 60 * 60 * 1000

export type TruckState = 'waiting' | 'driving' | 'arrived'

export interface TruckPosition {
  state: TruckState
  /** Miles driven so far, 0 before departure and the full distance after arrival. */
  mile: number
  coord: Coord
}

/** The moment heatmap hour `hour` stands for. */
export function heatmapTime(heatmap: HeatmapOut, hour: number): Date {
  return new Date(Date.parse(heatmap.start) + hour * HOUR_MS)
}

/** The heatmap hour closest to `iso`, clamped to the slider's range. */
export function heatmapHourOf(heatmap: HeatmapOut, iso: string): number {
  const hours = (Date.parse(iso) - Date.parse(heatmap.start)) / HOUR_MS
  return Math.min(heatmap.hours, Math.max(0, Math.round(hours)))
}

/**
 * Miles driven `hours` after departure. The checkpoints carry the planner's own
 * mile-to-ETA mapping, so interpolating between them matches the ETAs the user
 * reads in the table rather than re-estimating speed.
 */
export function mileAtHours(route: RouteOut, hours: number): number {
  const cps = route.checkpoints
  if (cps.length === 0 || hours <= 0) return 0
  const last = cps[cps.length - 1]!
  if (hours >= last.hoursFromDeparture) return route.distanceMi
  for (let i = 1; i < cps.length; i++) {
    const b = cps[i]!
    if (hours <= b.hoursFromDeparture) {
      const a = cps[i - 1]!
      const span = b.hoursFromDeparture - a.hoursFromDeparture
      const t = span === 0 ? 0 : (hours - a.hoursFromDeparture) / span
      return a.mile + (b.mile - a.mile) * t
    }
  }
  return route.distanceMi
}

/** One line for the heatmap slider: where the truck is at the hour shown. */
export function describeTruck(routeId: string, truck: TruckPosition): string {
  switch (truck.state) {
    case 'waiting':
      return 'Truck has not left yet'
    case 'arrived':
      return `Truck has arrived on Route ${routeId}`
    case 'driving':
      return `Truck at mile ${Math.round(truck.mile).toLocaleString()} on Route ${routeId}`
  }
}

/** Where the truck is on `route` at `at`, leaving at `departureAt`. */
export function truckPositionAt(
  route: RouteOut,
  departureAt: string,
  at: Date,
): TruckPosition {
  const hours = (at.getTime() - Date.parse(departureAt)) / HOUR_MS
  const duration = route.durationS / 3600
  const state: TruckState =
    hours < 0 ? 'waiting' : hours >= duration ? 'arrived' : 'driving'
  const mile = mileAtHours(route, hours)

  // The drawn geometry is simplified, so it is a little shorter than the road
  // distance; place the truck at the same fraction of it instead.
  const cumulative = cumulativeM(route.geometry)
  const fraction = route.distanceMi > 0 ? mile / route.distanceMi : 0
  const coord = pointAlong(
    route.geometry,
    cumulative,
    fraction * cumulative[cumulative.length - 1]!,
  )
  return { state, mile, coord }
}
