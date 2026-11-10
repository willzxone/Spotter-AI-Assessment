import type { ConditionKind, RiskLevelName } from '@/integrations/rpc/api.gen'

export interface RiskLevelMeta {
  label: string
  /** The backend's 0-4 score for the level; heatmap scores interpolate between these. */
  score: number
  /** Fill for the map, badges and legend. */
  color: string
  /** Text on top of `color`, chosen for contrast. */
  ink: string
}

/** Every risk level, mildest first. One palette for the map, badges and legend. */
export const RISK_LEVELS: Record<RiskLevelName, RiskLevelMeta> = {
  low: { label: 'Low', score: 0, color: '#15803d', ink: '#ffffff' },
  moderate: { label: 'Moderate', score: 1, color: '#eab308', ink: '#1c1917' },
  high: { label: 'High', score: 2, color: '#f97316', ink: '#1c1917' },
  severe: { label: 'Severe', score: 3, color: '#dc2626', ink: '#ffffff' },
  no_travel: { label: 'No Travel', score: 4, color: '#581c87', ink: '#ffffff' },
}

export const RISK_ORDER: readonly RiskLevelName[] = [
  'low',
  'moderate',
  'high',
  'severe',
  'no_travel',
]

/**
 * How the planner orders routes, as backend `modules/trips/ranking.py` applies them:
 * the first criterion that separates two routes decides. No Travel comes before
 * the brief's Severe so a route through No Travel can never win.
 */
export const RANKING_CRITERIA: readonly string[] = [
  'Fewest No Travel miles',
  'Fewest Severe miles',
  'Fewest High miles',
  'Lowest average risk',
  'Shortest travel time',
]

/** How each condition is named and how precisely its thresholds are written (as in the brief). */
export const CONDITIONS: Record<
  ConditionKind,
  { label: string; decimals: number }
> = {
  wind: { label: 'Wind', decimals: 0 },
  rain: { label: 'Rain', decimals: 2 },
  snow: { label: 'Snow', decimals: 1 },
}
