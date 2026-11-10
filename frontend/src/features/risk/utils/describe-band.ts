import type { BandOut } from '@/integrations/rpc/api.gen'

/**
 * A band as the brief's table writes it: `< 25`, `25–34`, `0.10–0.25`, `> 1.00`.
 *
 * Whole-number conditions (wind, in mph) show an exclusive upper bound as the
 * last whole value inside it, so [25, 35) reads `25–34`.
 */
export function describeBand(band: BandOut, decimals: number): string {
  const fmt = (value: number) => value.toFixed(decimals)
  const { min, max } = band

  if (min === null) {
    return max === null ? 'any' : `${band.maxInclusive ? '≤' : '<'} ${fmt(max)}`
  }
  if (max === null) return `${band.minInclusive ? '≥' : '>'} ${fmt(min)}`

  const top = decimals === 0 && !band.maxInclusive ? max - 1 : max
  return `${fmt(min)}–${fmt(top)}`
}
