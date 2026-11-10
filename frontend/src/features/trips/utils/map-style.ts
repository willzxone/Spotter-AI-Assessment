import type {
  DataDrivenPropertyValueSpecification,
  ExpressionSpecification,
} from 'maplibre-gl'
import { RISK_LEVELS } from '@/features/risk'
import { heatScoreKey } from './map-data'

const { low, moderate, high, severe, no_travel: noTravel } = RISK_LEVELS

/** A risk level's colour, read from a feature's `level` property. */
export const LEVEL_COLOR: ExpressionSpecification = [
  'match',
  ['get', 'level'],
  'low',
  low.color,
  'moderate',
  moderate.color,
  'high',
  high.color,
  'severe',
  severe.color,
  'no_travel',
  noTravel.color,
  '#64748b',
]

/** Heatmap colour: the 0-4 score blends between the level colours. */
export function heatColor(
  hour: number,
): DataDrivenPropertyValueSpecification<string> {
  return [
    'interpolate',
    ['linear'],
    ['coalesce', ['get', heatScoreKey(hour)], 0],
    low.score,
    low.color,
    moderate.score,
    moderate.color,
    high.score,
    high.color,
    severe.score,
    severe.color,
    noTravel.score,
    noTravel.color,
  ]
}

/**
 * Heatmap opacity: clear weather stays faint so a long green corridor does not
 * bury the route, and worse weather gets more solid as it gets worse.
 */
export function heatOpacity(
  hour: number,
): DataDrivenPropertyValueSpecification<number> {
  return [
    'interpolate',
    ['linear'],
    ['coalesce', ['get', heatScoreKey(hour)], 0],
    0,
    0.12,
    1,
    0.32,
    4,
    0.55,
  ]
}

export const SOURCE = {
  heatmap: 'heatmap',
  routes: 'routes',
  segments: 'segments',
  checkpoints: 'checkpoints',
  endpoints: 'endpoints',
  truck: 'truck',
} as const

export const LAYER = {
  heatmap: 'heatmap-fill',
  otherRoutes: 'routes-other',
  otherRoutesHit: 'routes-other-hit',
  casing: 'route-casing',
  segments: 'route-segments',
  checkpoints: 'checkpoints',
  checkpointActive: 'checkpoint-active',
  endpoints: 'endpoints',
  endpointLabels: 'endpoint-labels',
  truckHalo: 'truck-halo',
  truck: 'truck',
} as const

export const ALTERNATIVE_COLOR = '#64748b'
export const TRUCK_COLOR = '#0f172a'
