import type {
  Feature,
  FeatureCollection,
  LineString,
  Point,
  Polygon,
} from 'geojson'
import type {
  Coord,
  HeatmapOut,
  PointIn,
  RiskLevelName,
  RouteOut,
} from '@/integrations/rpc/api.gen'

export type RouteLineProps = { id: string }
export type SegmentProps = { level: RiskLevelName }
export type CheckpointProps = { index: number; level: RiskLevelName }
export type EndpointProps = { role: 'origin' | 'destination'; label: string }
/** `s0` ... `sN`: the cell's 0-4 score at each heatmap hour. */
export type HeatCellProps = Record<string, number>

export const EMPTY: FeatureCollection = {
  type: 'FeatureCollection',
  features: [],
}

function collection<TGeometry extends LineString | Point | Polygon, TProps>(
  features: Feature<TGeometry, TProps>[],
): FeatureCollection<TGeometry, TProps> {
  return { type: 'FeatureCollection', features }
}

function line<TProps>(
  coords: Coord[],
  properties: TProps,
): Feature<LineString, TProps> {
  return {
    type: 'Feature',
    properties,
    geometry: { type: 'LineString', coordinates: coords },
  }
}

function point<TProps>(
  coord: Coord,
  properties: TProps,
): Feature<Point, TProps> {
  return {
    type: 'Feature',
    properties,
    geometry: { type: 'Point', coordinates: coord },
  }
}

/** Every route's full line, for the alternatives and for clicking one to select it. */
export function routeLines(routes: readonly RouteOut[]) {
  return collection(routes.map((r) => line(r.geometry, { id: r.id })))
}

/** The selected route, cut into runs of one risk level each. */
export function segmentLines(route: RouteOut) {
  return collection(
    route.segments.map((s) => line(s.coords, { level: s.level })),
  )
}

export function checkpointPoints(route: RouteOut) {
  return collection(
    route.checkpoints.map((cp) =>
      point([cp.lon, cp.lat], { index: cp.index, level: cp.level }),
    ),
  )
}

/** `Joliet, Illinois, United States` -> `Joliet`: the map has no room for the rest. */
export function shortLabel(label: string | null | undefined, fallback: string) {
  const first = label?.split(',')[0]?.trim()
  return first || fallback
}

/** The trip's two ends, as the user picked them. */
export function endpointPoints(origin: PointIn, destination: PointIn) {
  return collection<Point, EndpointProps>([
    point([origin.lon, origin.lat], {
      role: 'origin',
      label: shortLabel(origin.label, 'Origin'),
    }),
    point([destination.lon, destination.lat], {
      role: 'destination',
      label: shortLabel(destination.label, 'Destination'),
    }),
  ])
}

export function truckPoint(coord: Coord) {
  return collection([point(coord, {})])
}

/** The heatmap property holding hour `hour`'s score. */
export const heatScoreKey = (hour: number) => `s${hour}`

/**
 * One square per forecast cell, centred on the cell's point (the backend snaps
 * to cell centres). Every hour's score rides along as a property, so moving the
 * slider only swaps a paint expression and never re-uploads the polygons.
 */
export function heatmapCells(heatmap: HeatmapOut) {
  const half = heatmap.cellDeg / 2
  return collection<Polygon, HeatCellProps>(
    heatmap.cells.map((cell) => {
      const props: HeatCellProps = {}
      cell.scores.forEach((score, hour) => {
        props[heatScoreKey(hour)] = score
      })
      const w = cell.lon - half
      const e = cell.lon + half
      const s = cell.lat - half
      const n = cell.lat + half
      return {
        type: 'Feature',
        properties: props,
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [w, s],
              [e, s],
              [e, n],
              [w, n],
              [w, s],
            ],
          ],
        },
      }
    }),
  )
}
