import { queryOptions } from '@tanstack/react-query'
import { rpc, rpcKey } from '@/integrations/rpc/client'
import type { SearchInput } from '@/integrations/rpc/api.gen'
import { MIN_QUERY_LENGTH, RESULT_LIMIT } from '../constants'

export function placeSearchQueryOptions(query: string) {
  const input: SearchInput = { query, limit: RESULT_LIMIT }
  return queryOptions({
    queryKey: rpcKey('geocoding/search', input),
    queryFn: ({ signal }) => rpc('geocoding/search', input, { signal }),
    enabled: query.length >= MIN_QUERY_LENGTH,
    // Place names do not move; the backend caches them for a day as well.
    staleTime: 60 * 60 * 1000,
  })
}
