import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MAX_LOAD_LB } from '@/features/trips/constants'
import { toDateTimeLocal } from '@/features/trips/utils/format'
import { toPlanInput, tripFormSchema } from '@/features/trips/utils/trip-form'
import type { TripFormValues } from '@/features/trips/utils/trip-form'
import type { Place } from '@/integrations/rpc/api.gen'

const NOW = new Date(2026, 10, 9, 12, 0)
const HOUR = 3_600_000

const chicago: Place = {
  id: 'sim-chicago',
  name: 'Chicago',
  label: 'Chicago, Illinois, United States',
  lat: 41.8781,
  lon: -87.6298,
  kind: 'city',
}
const atlanta: Place = {
  id: 'sim-atlanta',
  name: 'Atlanta',
  label: 'Atlanta, Georgia, United States',
  lat: 33.749,
  lon: -84.388,
  kind: 'city',
}

function values(overrides: Partial<TripFormValues> = {}): TripFormValues {
  return {
    origin: chicago,
    destination: atlanta,
    departure: toDateTimeLocal(new Date(NOW.getTime() + HOUR)),
    loadLb: 35_000,
    intervalMi: 25,
    ...overrides,
  }
}

/** Every issue's message, keyed by the field it belongs to. */
function issues(input: TripFormValues): Record<string, string> {
  const result = tripFormSchema.safeParse(input)
  if (result.success) return {}
  return Object.fromEntries(
    result.error.issues.map((i) => [i.path.join('.'), i.message]),
  )
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})
afterEach(() => {
  vi.useRealTimers()
})

describe('tripFormSchema', () => {
  it('accepts a complete trip', () => {
    expect(issues(values())).toEqual({})
  })

  it('asks for both ends of the trip', () => {
    expect(issues(values({ origin: null, destination: null }))).toEqual({
      origin: 'Choose where the trip starts.',
      destination: 'Choose where the trip ends.',
    })
  })

  it('allows a departure up to an hour ago as "leaving now", but no earlier', () => {
    const ago = (h: number) =>
      toDateTimeLocal(new Date(NOW.getTime() - h * HOUR))
    expect(issues(values({ departure: ago(0.5) }))).toEqual({})
    expect(issues(values({ departure: ago(2) }))).toEqual({
      departure: 'Departure is in the past.',
    })
  })

  it('refuses a departure beyond the forecast window', () => {
    const later = toDateTimeLocal(new Date(NOW.getTime() + 8 * 24 * HOUR))
    expect(issues(values({ departure: later })).departure).toMatch(
      /within the next 7 days/,
    )
  })

  it('needs an empty departure filled in', () => {
    expect(issues(values({ departure: '' }))).toEqual({
      departure: 'Pick a departure date and time.',
    })
  })

  it.each([
    [Number.NaN, 'Enter the load weight in pounds.'],
    [-1, 'Load cannot be negative.'],
    [1500.5, 'Use whole pounds.'],
    [
      MAX_LOAD_LB + 1,
      `Load must be at most ${MAX_LOAD_LB.toLocaleString()} lb.`,
    ],
  ])('rejects a load of %s', (loadLb, message) => {
    expect(issues(values({ loadLb }))).toEqual({ loadLb: message })
  })

  it('accepts an empty truck', () => {
    expect(issues(values({ loadLb: 0 }))).toEqual({})
  })

  it('refuses a trip that starts where it ends', () => {
    expect(issues(values({ destination: chicago }))).toEqual({
      destination: 'Destination must differ from the origin.',
    })
  })
})

describe('toPlanInput', () => {
  it('sends the chosen points with their labels and an absolute departure', () => {
    const form = values()
    expect(toPlanInput(form)).toEqual({
      origin: { lat: 41.8781, lon: -87.6298, label: chicago.label },
      destination: { lat: 33.749, lon: -84.388, label: atlanta.label },
      departureAt: new Date(NOW.getTime() + HOUR).toISOString(),
      loadLb: 35_000,
      intervalMi: 25,
    })
  })
})
