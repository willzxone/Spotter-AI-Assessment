import { describe, expect, it } from 'vitest'
import {
  checkpointPoints,
  endpointPoints,
  heatScoreKey,
  heatmapCells,
  routeLines,
  segmentLines,
  shortLabel,
} from '@/features/trips/utils/map-data'
import { plan, route } from './fixtures/plan'

describe('heatmapCells', () => {
  const { heatmap } = plan()
  const [cell] = heatmapCells(heatmap).features

  it('draws a closed square of cellDeg around the cell centre', () => {
    expect(cell?.geometry.coordinates).toEqual([
      [
        [-87.75, 41.75],
        [-87.5, 41.75],
        [-87.5, 42],
        [-87.75, 42],
        [-87.75, 41.75],
      ],
    ])
  })

  it("carries every hour's score, so the slider never re-uploads the polygons", () => {
    expect(cell?.properties).toEqual({ s0: 0, s1: 1, s2: 4 })
    expect(heatScoreKey(2)).toBe('s2')
  })
})

describe('route features', () => {
  const r = route()

  it('tags each line with its route id', () => {
    const b = route({ id: 'B', recommended: false })
    expect(routeLines([r, b]).features.map((f) => f.properties.id)).toEqual([
      'A',
      'B',
    ])
  })

  it('colours segments and checkpoints by level', () => {
    expect(segmentLines(r).features[0]?.properties).toEqual({ level: 'low' })
    const points = checkpointPoints(r).features
    expect(points).toHaveLength(5)
    expect(points[2]?.properties).toEqual({ index: 2, level: 'low' })
  })
})

describe('endpoint labels', () => {
  it('keeps only the place name', () => {
    expect(shortLabel('Joliet, Illinois, United States', 'Origin')).toBe(
      'Joliet',
    )
  })

  it('falls back when the user picked a point without a label', () => {
    expect(shortLabel(null, 'Origin')).toBe('Origin')
    expect(shortLabel('  ', 'Origin')).toBe('Origin')
    const points = endpointPoints(
      { lat: 1, lon: 2 },
      { lat: 3, lon: 4, label: 'Dallas, Texas' },
    ).features
    expect(points.map((p) => p.properties)).toEqual([
      { role: 'origin', label: 'Origin' },
      { role: 'destination', label: 'Dallas' },
    ])
    expect(points[0]?.geometry.coordinates).toEqual([2, 1])
  })
})
