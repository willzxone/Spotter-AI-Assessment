import type {
  CheckpointOut,
  Coord,
  PlanOutput,
  RiskLevelName,
  RouteOut,
} from '@/integrations/rpc/api.gen'

export const DEPARTURE = '2026-11-10T14:00:00Z'

/** A straight 100-mile road due east along 41.9° N, sampled every 0.1°. */
export const GEOMETRY: Coord[] = Array.from({ length: 21 }, (_, i) => [
  -88 + i * 0.0971,
  41.9,
])

/** Checkpoints every 25 mi at a steady 50 mph: mile m is reached at m / 50 hours. */
export function checkpoint(
  index: number,
  mile: number,
  overrides: Partial<CheckpointOut> = {},
): CheckpointOut {
  const hours = mile / 50
  return {
    index,
    mile,
    lat: 41.9,
    lon: -88 + (mile / 100) * 1.942,
    eta: new Date(Date.parse(DEPARTURE) + hours * 3_600_000).toISOString(),
    hoursFromDeparture: hours,
    level: 'low',
    windLevel: 'low',
    rainLevel: 'low',
    snowLevel: 'low',
    windMph: 8,
    gustMph: 14,
    rainInHr: 0,
    snowInHr: 0,
    drivers: [],
    coversFromMi: Math.max(0, mile - 12.5),
    coversToMi: Math.min(100, mile + 12.5),
    ...overrides,
  }
}

export function route(overrides: Partial<RouteOut> = {}): RouteOut {
  const worst: RiskLevelName = overrides.risk?.worst ?? 'low'
  return {
    id: 'A',
    summary: 'I 88, I 290',
    distanceMi: 100,
    durationS: 2 * 3600,
    arrivalAt: '2026-11-10T16:00:00Z',
    rank: 1,
    recommended: true,
    verdict: 'Recommended: the lowest average risk of the three routes.',
    risk: {
      worst,
      average: 0,
      miles: { low: 100, moderate: 0, high: 0, severe: 0, noTravel: 0 },
    },
    geometry: GEOMETRY,
    segments: [{ level: 'low', fromMi: 0, toMi: 100, coords: GEOMETRY }],
    checkpoints: [0, 25, 50, 75, 100].map((mile, i) => checkpoint(i, mile)),
    ...overrides,
  }
}

export function plan(overrides: Partial<PlanOutput> = {}): PlanOutput {
  const routes = overrides.routes ?? [route()]
  return {
    departureAt: DEPARTURE,
    loadLb: 35_000,
    intervalMi: 25,
    recommendedId: routes.find((r) => r.recommended)?.id ?? 'A',
    routes,
    heatmap: {
      start: DEPARTURE,
      hours: 48,
      cellDeg: 0.25,
      cells: [{ lat: 41.875, lon: -87.625, scores: [0, 1, 4] }],
    },
    warnings: [],
    sources: { routing: 'osrm', weather: 'open-meteo' },
    ...overrides,
  }
}
