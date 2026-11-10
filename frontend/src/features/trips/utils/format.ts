import type {
  CheckpointOut,
  ConditionKind,
  MilesByLevelOut,
  RiskLevelName,
} from '@/integrations/rpc/api.gen'

const MILES_KEY: Record<RiskLevelName, keyof MilesByLevelOut> = {
  low: 'low',
  moderate: 'moderate',
  high: 'high',
  severe: 'severe',
  no_travel: 'noTravel',
}

/** A route's miles at each level, mildest first, leaving out levels it never reaches. */
export function milesBreakdown(
  miles: MilesByLevelOut,
  order: readonly RiskLevelName[],
): { level: RiskLevelName; miles: number }[] {
  return order
    .map((level) => ({ level, miles: miles[MILES_KEY[level]] }))
    .filter((part) => part.miles > 0)
}

export interface Reading {
  kind: ConditionKind
  label: string
  value: string
  level: RiskLevelName
}

/** A checkpoint's three conditions, written as precisely as the brief's table. */
export function readings(cp: CheckpointOut): Reading[] {
  return [
    {
      kind: 'wind',
      label: 'Wind',
      value: `${Math.round(cp.windMph)} mph`,
      level: cp.windLevel,
    },
    {
      kind: 'rain',
      label: 'Rain',
      value: `${cp.rainInHr.toFixed(2)} in/hr`,
      level: cp.rainLevel,
    },
    {
      kind: 'snow',
      label: 'Snow',
      value: `${cp.snowInHr.toFixed(1)} in/hr`,
      level: cp.snowLevel,
    },
  ]
}

export function readingOf(cp: CheckpointOut, kind: ConditionKind): Reading {
  const reading = readings(cp).find((r) => r.kind === kind)
  if (!reading) throw new Error(`no ${kind} reading`)
  return reading
}

/** `13 h 40 min`, or `45 min` under an hour. */
export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} min`
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

/** `588.8 mi` under 1,000 miles, `1,204 mi` above. */
export function formatMiles(miles: number): string {
  const digits = miles < 1000 ? 1 : 0
  return `${miles.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} mi`
}

/** A short local date-time, e.g. `Tue 3:45 PM`. */
export function formatEta(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** A full local date-time, e.g. `Tue, Nov 10, 3:45 PM`. */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** A `Date` as the local `YYYY-MM-DDTHH:mm` that `<input type="datetime-local">` reads. */
export function toDateTimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/** Now, rounded up to the next quarter hour: the form's default departure. */
export function nextQuarterHour(now: Date = new Date()): Date {
  const step = 15 * 60 * 1000
  return new Date(Math.ceil(now.getTime() / step) * step)
}
