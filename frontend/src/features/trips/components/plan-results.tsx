import { CircleAlert, Loader2 } from 'lucide-react'
import { cn } from 'cn'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import type { PlanOutput, RouteOut } from '@/integrations/rpc/api.gen'
import { formatDateTime } from '../utils/format'
import { PlanNotices } from './plan-notices'
import { RouteCard } from './route-card'

interface Props {
  plan: PlanOutput | null
  routes: RouteOut[]
  selectedId: string | null
  isPlanning: boolean
  isOutdated: boolean
  error: string | null
  onSelectRoute: (id: string) => void
}

export function PlanResults({
  plan,
  routes,
  selectedId,
  isPlanning,
  isOutdated,
  error,
  onSelectRoute,
}: Props) {
  if (error) {
    return (
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>Could not plan this trip</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (!plan) {
    if (isPlanning) {
      return (
        <div aria-busy className="flex flex-col gap-3">
          <span className="sr-only">Planning routes…</span>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )
    }
    return (
      <p className="text-muted-foreground text-sm">
        Choose an origin and destination to compare up to three routes. Each is
        scored for wind, rain and snow at the time the truck reaches every
        checkpoint, with the load weight raising the wind risk, and the safest
        one is recommended.
      </p>
    )
  }

  return (
    <section
      aria-label="Route options"
      aria-busy={isPlanning}
      className={cn(
        'flex flex-col gap-3 transition-opacity',
        isOutdated && 'opacity-60',
      )}
    >
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="font-semibold">Routes</h2>
        <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
          {isPlanning ? (
            <>
              <Loader2 className="size-3 animate-spin" /> Updating…
            </>
          ) : (
            <>
              Departs {formatDateTime(plan.departureAt)} ·{' '}
              {plan.loadLb.toLocaleString()} lb
            </>
          )}
        </span>
      </header>
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          selected={route.id === selectedId}
          onSelect={onSelectRoute}
        />
      ))}
      <PlanNotices plan={plan} />
    </section>
  )
}
