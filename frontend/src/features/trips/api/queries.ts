import { queryOptions } from '@tanstack/react-query'
import type { PlanInput, PlanOutput } from '@/integrations/rpc/api.gen'
import { rpc, rpcKey } from '@/integrations/rpc/client'
import { PLAN_STALE_MS } from '../constants'

/**
 * A plan together with the input it answers. While a new plan loads, the
 * previous one stays on screen, and its endpoints must still match its routes.
 */
export interface PlannedTrip {
  input: PlanInput
  plan: PlanOutput
}

/** A plan is a read: the same input within a few minutes is the same answer. */
export function planQueryOptions(input: PlanInput | null) {
  return queryOptions({
    queryKey: rpcKey('trips/plan', input),
    queryFn: async ({ signal }): Promise<PlannedTrip> => {
      if (!input) throw new Error('planQueryOptions ran without an input')
      return { input, plan: await rpc('trips/plan', input, { signal }) }
    },
    enabled: input !== null,
    staleTime: PLAN_STALE_MS,
  })
}
