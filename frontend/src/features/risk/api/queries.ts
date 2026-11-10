import { queryOptions } from '@tanstack/react-query'
import { rpc, rpcKey } from '@/integrations/rpc/client'

/** The risk table and load rules. They only change with a deploy. */
export function riskRulesQueryOptions() {
  return queryOptions({
    queryKey: rpcKey('risk/rules', null),
    queryFn: ({ signal }) => rpc('risk/rules', undefined, { signal }),
    staleTime: Infinity,
  })
}
