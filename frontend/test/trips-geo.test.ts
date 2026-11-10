import { describe, expect, it } from 'vitest'
import {
  boundsOf,
  cumulativeM,
  haversineM,
  pointAlong,
} from '@/features/trips/utils/geo'
import type { Coord } from '@/integrations/rpc/api.gen'

const CHICAGO: Coord = [-87.6298, 41.8781]
const ATLANTA: Coord = [-84.388, 33.749]

describe('haversineM', () => {
  it('measures Chicago to Atlanta as the crow flies (about 945 km)', () => {
    const d = haversineM(CHICAGO, ATLANTA)
    expect(d).toBeGreaterThan(935_000)
    expect(d).toBeLessThan(955_000)
  })

  it('is zero for the same point and symmetric', () => {
    expect(haversineM(CHICAGO, CHICAGO)).toBe(0)
    expect(haversineM(CHICAGO, ATLANTA)).toBeCloseTo(
      haversineM(ATLANTA, CHICAGO),
      6,
    )
  })
})

describe('pointAlong', () => {
  // Two equal legs along the equator, where a degree of longitude is uniform.
  const line: Coord[] = [
    [0, 0],
    [1, 0],
    [2, 0],
  ]
  const cumulative = cumulativeM(line)

  it('starts at 0 and adds each leg', () => {
    expect(cumulative[0]).toBe(0)
    expect(cumulative[2]).toBeCloseTo(2 * cumulative[1]!, 6)
  })

  it('interpolates inside a leg', () => {
    const [lon, lat] = pointAlong(line, cumulative, cumulative[1]! * 1.5)
    expect(lon).toBeCloseTo(1.5, 6)
    expect(lat).toBe(0)
  })

  it('lands exactly on a vertex', () => {
    expect(pointAlong(line, cumulative, cumulative[1]!)).toEqual([1, 0])
  })

  it('clamps to the ends', () => {
    expect(pointAlong(line, cumulative, -5)).toEqual([0, 0])
    expect(pointAlong(line, cumulative, 1e12)).toEqual([2, 0])
  })
})

describe('boundsOf', () => {
  it('wraps every point', () => {
    expect(boundsOf([CHICAGO, ATLANTA])).toEqual([
      [-87.6298, 33.749],
      [-84.388, 41.8781],
    ])
  })

  it('is null for nothing', () => {
    expect(boundsOf([])).toBeNull()
  })
})
