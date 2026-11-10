import { QueryClient } from '@tanstack/react-query'
import { RpcError } from '@/integrations/rpc/client'

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // One retry, and only for failures a retry can fix. A 4xx is the same
        // answer the second time, and planning calls are rate limited.
        retry: (failureCount, error) =>
          failureCount < 1 && error instanceof RpcError && error.transient,
        // A plan costs routing and forecast calls; coming back to the tab is not a reason to redo it.
        refetchOnWindowFocus: false,
      },
    },
  })
}
