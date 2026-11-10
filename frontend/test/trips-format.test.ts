import { describe, expect, it } from 'vitest'
import { RISK_ORDER } from '@/features/risk'
import {
  formatDuration,
  formatMiles,
  milesBreakdown,
  nextQuarterHour,
  readingOf,
  readings,
  toDateTimeLocal,
} from '@/features/trips/utils/format'
import { checkpoint } from './fixtures/plan'

describe('formatDuration', () => {
  it.each([
    [45 * 60, '45 min'],
    [3600, '1 h'],
    [13 * 3600 + 40 * 60, '13 h 40 min'],
    // 59.6 minutes rounds up to the hour rather than showing "0 h 60 min".
    [3576, '1 h'],
  ])('%i s reads as %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})

describe('formatMiles', () => {
  it('keeps a decimal under 1,000 miles and drops it above', () => {
    expect(formatMiles(588.84)).toBe('588.8 mi')
    expect(formatMiles(1204.4)).toBe('1,204 mi')
  })
})

describe('datetime-local helpers', () => {
  it('writes the local wall-clock time the input expects', () => {
    expect(toDateTimeLocal(new Date(2026, 10, 9, 7, 5))).toBe(
      '2026-11-09T07:05',
    )
  })

  it('rounds the default departure up to the next quarter hour', () => {
    expect(nextQuarterHour(new Date(2026, 10, 9, 7, 5, 30))).toEqual(
      new Date(2026, 10, 9, 7, 15),
    )
    // Already on a quarter hour: stays put.
    expect(nextQuarterHour(new Date(2026, 10, 9, 7, 30))).toEqual(
      new Date(2026, 10, 9, 7, 30),
    )
  })
})

describe('milesBreakdown', () => {
  it('orders levels mildest first, maps noTravel and drops empty levels', () => {
    const parts = milesBreakdown(
      { low: 80, moderate: 0, high: 5, severe: 0, noTravel: 15 },
      RISK_ORDER,
    )
    expect(parts).toEqual([
      { level: 'low', miles: 80 },
      { level: 'high', miles: 5 },
      { level: 'no_travel', miles: 15 },
    ])
  })
})

describe('readings', () => {
  it("writes each condition as precisely as the brief's table", () => {
    const cp = checkpoint(0, 0, {
      windMph: 36.6,
      rainInHr: 0.256,
      snowInHr: 1.04,
      windLevel: 'high',
      rainLevel: 'severe',
      snowLevel: 'high',
    })
    expect(readings(cp)).toEqual([
      { kind: 'wind', label: 'Wind', value: '37 mph', level: 'high' },
      { kind: 'rain', label: 'Rain', value: '0.26 in/hr', level: 'severe' },
      { kind: 'snow', label: 'Snow', value: '1.0 in/hr', level: 'high' },
    ])
    expect(readingOf(cp, 'rain').level).toBe('severe')
  })
})
