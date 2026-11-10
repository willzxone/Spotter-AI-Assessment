import { z } from 'zod'
import type {
  CheckpointIntervalMi,
  Place,
  PlanInput,
} from '@/integrations/rpc/api.gen'
import {
  DEFAULT_CHECKPOINT_INTERVAL_MI,
  DEFAULT_LOAD_LB,
  DEPARTURE_GRACE_MS,
  DEPARTURE_MAX_AHEAD_DAYS,
  MAX_LOAD_LB,
} from '../constants'
import { nextQuarterHour, toDateTimeLocal } from './format'

export interface TripFormValues {
  origin: Place | null
  destination: Place | null
  /** Local `YYYY-MM-DDTHH:mm`, as `<input type="datetime-local">` reads and writes it. */
  departure: string
  /** NaN while the input is empty. */
  loadLb: number
  intervalMi: CheckpointIntervalMi
}

export function defaultTripValues(): TripFormValues {
  return {
    origin: null,
    destination: null,
    departure: toDateTimeLocal(nextQuarterHour()),
    loadLb: DEFAULT_LOAD_LB,
    intervalMi: DEFAULT_CHECKPOINT_INTERVAL_MI,
  }
}

/** The earliest and latest departure the server accepts, right now. */
export function departureWindow(now: number = Date.now()) {
  return {
    earliest: now - DEPARTURE_GRACE_MS,
    latest: now + DEPARTURE_MAX_AHEAD_DAYS * 24 * 60 * 60 * 1000,
  }
}

function placeField(message: string) {
  // Typed `boolean`, not inferred as a type predicate: a failed refine does not
  // stop the object-level check below, which can still see `null`.
  return z
    .custom<Place | null>()
    .refine((place): boolean => place !== null, { message })
}

/** The same rules the backend applies, so most mistakes never cost a request. */
export const tripFormSchema = z
  .object({
    origin: placeField('Choose where the trip starts.'),
    destination: placeField('Choose where the trip ends.'),
    departure: z.string().superRefine((value, ctx) => {
      const at = new Date(value).getTime()
      if (!value || Number.isNaN(at)) {
        ctx.addIssue({
          code: 'custom',
          message: 'Pick a departure date and time.',
        })
        return
      }
      const { earliest, latest } = departureWindow()
      if (at < earliest) {
        ctx.addIssue({ code: 'custom', message: 'Departure is in the past.' })
      } else if (at > latest) {
        ctx.addIssue({
          code: 'custom',
          message: `Departure must be within the next ${DEPARTURE_MAX_AHEAD_DAYS} days; the forecast is not reliable further out.`,
        })
      }
    }),
    loadLb: z
      .number({ error: 'Enter the load weight in pounds.' })
      .int('Use whole pounds.')
      .min(0, 'Load cannot be negative.')
      .max(
        MAX_LOAD_LB,
        `Load must be at most ${MAX_LOAD_LB.toLocaleString()} lb.`,
      ),
    intervalMi: z.union([z.literal(10), z.literal(25), z.literal(50)]),
  })
  // Runs even when a field failed, so a missing place is skipped, not dereferenced.
  .superRefine(({ origin, destination }, ctx) => {
    if (!origin || !destination) return
    if (origin.lat === destination.lat && origin.lon === destination.lon) {
      ctx.addIssue({
        code: 'custom',
        path: ['destination'],
        message: 'Destination must differ from the origin.',
      })
    }
  })

/** The validated form as the API's `trips/plan` input. */
export function toPlanInput(values: TripFormValues): PlanInput {
  const point = (place: Place | null) => {
    if (!place) throw new Error('toPlanInput called before validation')
    return { lat: place.lat, lon: place.lon, label: place.label }
  }
  return {
    origin: point(values.origin),
    destination: point(values.destination),
    departureAt: new Date(values.departure).toISOString(),
    loadLb: values.loadLb,
    intervalMi: values.intervalMi,
  }
}
