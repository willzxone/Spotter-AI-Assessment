import { cn } from 'cn'
import type { RiskLevelName } from '@/integrations/rpc/api.gen'
import { RISK_LEVELS } from '../constants'

interface Props {
  level: RiskLevelName
  className?: string
}

export function RiskBadge({ level, className }: Props) {
  const { label, color, ink } = RISK_LEVELS[level]
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium whitespace-nowrap',
        className,
      )}
      style={{ backgroundColor: color, color: ink }}
    >
      {label}
    </span>
  )
}
