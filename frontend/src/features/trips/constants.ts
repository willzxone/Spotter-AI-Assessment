import type { CheckpointIntervalMi } from '@/integrations/rpc/api.gen'

/** Mirrors backend `modules/trips/constants.py`; the server enforces the same limits. */
export const CHECKPOINT_INTERVALS_MI: readonly CheckpointIntervalMi[] = [
  10, 25, 50,
]
export const DEFAULT_CHECKPOINT_INTERVAL_MI: CheckpointIntervalMi = 25

/** A gross-weight cap well above any permitted load, to catch typos. */
export const MAX_LOAD_LB = 200_000
/** A typical loaded dry van, so the form starts with a sensible weight. */
export const DEFAULT_LOAD_LB = 35_000

/** A departure up to this far in the past still counts as "leaving now". */
export const DEPARTURE_GRACE_MS = 60 * 60 * 1000
/** Further ahead than this, the forecast is too uncertain to plan against. */
export const DEPARTURE_MAX_AHEAD_DAYS = 7

/** How long a plan stays fresh before another submit re-plans it. */
export const PLAN_STALE_MS = 5 * 60 * 1000

/** Map line widths: the selected route stands out, alternatives stay readable. */
export const ROUTE_WIDTH = { selected: 6, other: 3.5 } as const

/** How long each forecast hour shows while the heatmap plays. */
export const PLAYBACK_STEP_MS = 700

/** Display names for the backend adapters a plan reports in `sources`. */
export const SOURCE_LABELS: Record<string, string> = {
  osrm: 'OSRM',
  'open-meteo': 'Open-Meteo',
  simulated: 'Simulated',
  off: 'Off',
}
