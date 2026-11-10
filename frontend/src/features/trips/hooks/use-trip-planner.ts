import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { PlanInput } from '@/integrations/rpc/api.gen'
import { errorMessage } from '@/integrations/rpc/client'
import { planQueryOptions } from '../api/queries'

/** The trip the user asked for and the plan that answers it. */
export function useTripPlanner() {
  const [input, setInput] = useState<PlanInput | null>(null)
  const query = useQuery({
    ...planQueryOptions(input),
    // Keep the last plan on screen while the next one loads.
    placeholderData: keepPreviousData,
  })

  function submit(next: PlanInput) {
    const same =
      input !== null && JSON.stringify(next) === JSON.stringify(input)
    // The same trip again is a retry after an error, or a refresh of an old answer.
    if (same) {
      if (query.isError || query.isStale) void query.refetch()
      return
    }
    setInput(next)
  }

  return {
    submit,
    trip: query.data ?? null,
    isPlanning: query.isFetching,
    /** The plan on screen answers an earlier trip; a new one is on its way. */
    isOutdated: query.isPlaceholderData,
    error: query.isError ? errorMessage(query.error) : null,
  }
}
