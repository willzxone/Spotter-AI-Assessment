import { cn } from 'cn'
import { RISK_LEVELS, RISK_ORDER } from '../constants'

interface Props {
  className?: string
}

export function RiskLegend({ className }: Props) {
  return (
    <ul className={cn('flex flex-col gap-1 text-xs', className)}>
      {RISK_ORDER.map((level) => (
        <li key={level} className="flex items-center gap-2">
          <span
            aria-hidden
            className="size-3 shrink-0 rounded-sm"
            style={{ backgroundColor: RISK_LEVELS[level].color }}
          />
          {RISK_LEVELS[level].label}
        </li>
      ))}
    </ul>
  )
}
