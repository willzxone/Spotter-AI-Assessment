import { Info, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import type { PlanOutput } from '@/integrations/rpc/api.gen'
import { SOURCE_LABELS } from '../constants'

interface Props {
  plan: PlanOutput
}

/** The planner's warnings, and where the routes and weather came from. */
export function PlanNotices({ plan }: Props) {
  const { routing, weather } = plan.sources
  const simulated = routing === 'simulated' || weather === 'simulated'
  return (
    <div className="flex flex-col gap-3">
      {plan.warnings.length > 0 && (
        <Alert>
          <TriangleAlert />
          <AlertTitle>Heads up</AlertTitle>
          <AlertDescription>
            <ul className="list-disc pl-4">
              {plan.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
      {simulated && (
        <Alert>
          <Info />
          <AlertTitle>Simulated data</AlertTitle>
          <AlertDescription>
            The server is running without live providers, so routes or weather
            are generated for the demo rather than real.
          </AlertDescription>
        </Alert>
      )}
      <p className="text-muted-foreground text-xs">
        Routing: {SOURCE_LABELS[routing] ?? routing} · Weather:{' '}
        {SOURCE_LABELS[weather] ?? weather}
      </p>
    </div>
  )
}
