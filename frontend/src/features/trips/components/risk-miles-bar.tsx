import { RISK_LEVELS, RISK_ORDER } from '@/features/risk'
import type { MilesByLevelOut } from '@/integrations/rpc/api.gen'
import { milesBreakdown } from '../utils/format'

interface Props {
  miles: MilesByLevelOut
}

/** How much of the route is at each risk level, as one stacked bar. */
export function RiskMilesBar({ miles }: Props) {
  const parts = milesBreakdown(miles, RISK_ORDER)
  const total = parts.reduce((sum, p) => sum + p.miles, 0)
  const text = parts
    .map((p) => `${RISK_LEVELS[p.level].label} ${Math.round(p.miles)} mi`)
    .join(' · ')
  return (
    <span className="flex flex-col gap-1">
      <span
        aria-hidden
        className="bg-muted flex h-2 w-full overflow-hidden rounded-full"
      >
        {total > 0 &&
          parts.map((p) => (
            <span
              key={p.level}
              className="h-full"
              style={{
                width: `${(p.miles / total) * 100}%`,
                backgroundColor: RISK_LEVELS[p.level].color,
              }}
            />
          ))}
      </span>
      <span className="text-muted-foreground text-xs">{text}</span>
    </span>
  )
}
