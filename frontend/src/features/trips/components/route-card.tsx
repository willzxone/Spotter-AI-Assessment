import { cn } from 'cn'
import { Badge } from '@/components/ui/badge'
import { RiskBadge } from '@/features/risk'
import type { RouteOut } from '@/integrations/rpc/api.gen'
import { formatDuration, formatEta, formatMiles } from '../utils/format'
import { RiskMilesBar } from './risk-miles-bar'

interface Props {
  route: RouteOut
  selected: boolean
  onSelect: (id: string) => void
}

/** One route option. A button, so only phrasing content (spans) inside. */
export function RouteCard({ route, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(route.id)}
      className={cn(
        'flex w-full flex-col gap-2 rounded-lg border p-3 text-left text-sm transition-colors',
        'hover:bg-accent/50 focus-visible:ring-ring/50 outline-none focus-visible:ring-[3px]',
        selected && 'border-primary bg-accent/40 ring-primary ring-1',
      )}
    >
      <span className="flex items-center gap-2">
        <span className="font-semibold">Route {route.id}</span>
        {route.recommended && <Badge>Recommended</Badge>}
        <span className="text-muted-foreground ml-auto text-xs">Worst</span>
        <RiskBadge level={route.risk.worst} />
      </span>

      <span className="text-muted-foreground truncate text-xs">
        via {route.summary}
      </span>

      <span className="grid grid-cols-3 gap-2">
        <span className="flex flex-col">
          <span className="text-muted-foreground text-xs">Distance</span>
          <span className="font-medium tabular-nums">
            {formatMiles(route.distanceMi)}
          </span>
        </span>
        <span className="flex flex-col">
          <span className="text-muted-foreground text-xs">Drive time</span>
          <span className="font-medium tabular-nums">
            {formatDuration(route.durationS)}
          </span>
        </span>
        <span className="flex flex-col">
          <span className="text-muted-foreground text-xs">Arrives</span>
          <span className="font-medium tabular-nums">
            {formatEta(route.arrivalAt)}
          </span>
        </span>
      </span>

      <RiskMilesBar miles={route.risk.miles} />

      <span className="text-xs">{route.verdict}</span>
    </button>
  )
}
