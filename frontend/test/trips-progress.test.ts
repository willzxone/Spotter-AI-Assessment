import { describe, expect, it } from 'vitest'
import {
  describeTruck,
  heatmapHourOf,
  heatmapTime,
  mileAtHours,
  truckPositionAt,
} from '@/features/trips/utils/progress'
import { DEPARTURE, GEOMETRY, plan, route } from './fixtures/plan'

const at = (hours: number) =>
  new Date(Date.parse(DEPARTURE) + hours * 3_600_000)

describe('mileAtHours', () => {
  const r = route()

  it('follows the checkpoint ETAs between checkpoints', () => {
    // 50 mph: 1.25 h in is mile 62.5, halfway between the 50 and 75 checkpoints.
    expect(mileAtHours(r, 1.25)).toBeCloseTo(62.5, 6)
  })

  it('is 0 before departure and the full distance after arrival', () => {
    expect(mileAtHours(r, -3)).toBe(0)
    expect(mileAtHours(r, 9)).toBe(100)
  })
})

describe('truckPositionAt', () => {
  const r = route()

  it('waits at the origin before departure', () => {
    const truck = truckPositionAt(r, DEPARTURE, at(-1))
    expect(truck.state).toBe('waiting')
    expect(truck.coord).toEqual(GEOMETRY[0])
  })

  it('drives along the line, at the same fraction of it as of the road', () => {
    const truck = truckPositionAt(r, DEPARTURE, at(1))
    expect(truck.state).toBe('driving')
    expect(truck.mile).toBeCloseTo(50, 6)
    const first = GEOMETRY[0]!
    const last = GEOMETRY[GEOMETRY.length - 1]!
    expect(truck.coord[0]).toBeCloseTo((first[0] + last[0]) / 2, 3)
  })

  it('has arrived once the drive time is up', () => {
    const truck = truckPositionAt(r, DEPARTURE, at(2))
    expect(truck.state).toBe('arrived')
    expect(truck.coord).toEqual(GEOMETRY[GEOMETRY.length - 1])
  })
})

describe('heatmap hours', () => {
  const { heatmap } = plan()

  it('maps an hour to its moment and back', () => {
    const t = heatmapTime(heatmap, 5)
    expect(t.toISOString()).toBe('2026-11-10T19:00:00.000Z')
    expect(heatmapHourOf(heatmap, t.toISOString())).toBe(5)
  })

  it('rounds to the nearest hour and clamps to the slider', () => {
    expect(heatmapHourOf(heatmap, '2026-11-10T16:40:00Z')).toBe(3)
    expect(heatmapHourOf(heatmap, '2026-11-09T00:00:00Z')).toBe(0)
    expect(heatmapHourOf(heatmap, '2026-11-30T00:00:00Z')).toBe(48)
  })
})

describe('describeTruck', () => {
  it('says where the truck is in words', () => {
    const r = route()
    expect(describeTruck('A', truckPositionAt(r, DEPARTURE, at(-1)))).toBe(
      'Truck has not left yet',
    )
    expect(describeTruck('A', truckPositionAt(r, DEPARTURE, at(1)))).toBe(
      'Truck at mile 50 on Route A',
    )
    expect(describeTruck('A', truckPositionAt(r, DEPARTURE, at(3)))).toBe(
      'Truck has arrived on Route A',
    )
  })
})
