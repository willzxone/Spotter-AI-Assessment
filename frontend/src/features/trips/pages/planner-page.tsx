import { Truck } from 'lucide-react'
import { RiskRulesDialog } from '@/features/risk'
import { CheckpointCard } from '../components/checkpoint-card'
import { CheckpointTable } from '../components/checkpoint-table'
import { HeatmapSlider } from '../components/heatmap-slider'
import { PlanResults } from '../components/plan-results'
import { RouteMap } from '../components/route-map'
import { TripForm } from '../components/trip-form'
import { usePlanView } from '../hooks/use-plan-view'
import { useTripPlanner } from '../hooks/use-trip-planner'

export function PlannerPage() {
  const planner = useTripPlanner()
  const plan = planner.trip?.plan ?? null
  const view = usePlanView(plan)

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh lg:flex-row">
      <aside className="flex flex-col border-b lg:w-[26rem] lg:shrink-0 lg:border-r lg:border-b-0">
        <header className="flex items-center gap-2 border-b px-4 py-3">
          <Truck aria-hidden className="size-5" />
          <h1 className="font-semibold">Weather-Aware Truck Routing</h1>
          <div className="ml-auto">
            <RiskRulesDialog />
          </div>
        </header>
        <div className="flex flex-col gap-6 p-4 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
          <TripForm onPlan={planner.submit} isPlanning={planner.isPlanning} />
          <PlanResults
            plan={plan}
            routes={view.rankedRoutes}
            selectedId={view.route?.id ?? null}
            isPlanning={planner.isPlanning}
            isOutdated={planner.isOutdated}
            error={planner.error}
            onSelectRoute={view.selectRoute}
          />
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col lg:min-h-0">
        <RouteMap
          className="h-[65vh] lg:h-auto lg:min-h-0 lg:flex-1"
          input={planner.trip?.input ?? null}
          plan={plan}
          route={view.route}
          hour={view.hour}
          truck={view.truck?.coord ?? null}
          inspected={view.inspected}
          onSelectRoute={view.selectRoute}
          onInspect={view.inspect}
        >
          {view.inspected && (
            <div className="absolute top-3 left-3 z-10">
              <CheckpointCard
                checkpoint={view.inspected}
                onClose={view.closeInspector}
              />
            </div>
          )}
          {view.route && view.at && (
            <div className="absolute inset-x-3 bottom-8 z-10 mx-auto max-w-2xl">
              <HeatmapSlider
                hour={view.hour}
                maxHour={view.maxHour}
                at={view.at}
                routeId={view.route.id}
                truck={view.truck}
                playing={view.playing}
                onHourChange={view.setHour}
                onTogglePlayback={view.togglePlayback}
              />
            </div>
          )}
        </RouteMap>

        {plan && view.route && (
          <section
            aria-labelledby="checkpoints-heading"
            className="flex flex-col border-t lg:h-[36%] lg:min-h-48"
          >
            <header className="flex flex-wrap items-baseline gap-x-2 px-4 py-2">
              <h2 id="checkpoints-heading" className="text-sm font-semibold">
                Checkpoints on Route {view.route.id}
              </h2>
              <span className="text-muted-foreground text-xs">
                every {plan.intervalMi} mi · {view.route.checkpoints.length}{' '}
                checkpoints · pick one to see it on the map
              </span>
            </header>
            {/* The table's own container scrolls, so its sticky header stays put. */}
            <div className="min-h-0 flex-1 [&_[data-slot=table-container]]:lg:h-full [&_[data-slot=table-container]]:lg:overflow-auto">
              <CheckpointTable
                checkpoints={view.route.checkpoints}
                inspected={view.inspected?.index ?? null}
                onInspect={view.inspect}
              />
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
