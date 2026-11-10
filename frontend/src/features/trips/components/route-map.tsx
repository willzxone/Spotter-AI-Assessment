import { cn } from 'cn'
import type { ReactNode } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { useRouteMap } from '../hooks/use-route-map'
import type { RouteMapOptions } from '../hooks/use-route-map'

interface Props extends RouteMapOptions {
  className?: string
  /** Overlays laid over the map: the inspector, the heatmap slider. */
  children?: ReactNode
}

export function RouteMap({ className, children, ...options }: Props) {
  const { containerRef, ready } = useRouteMap(options)
  return (
    <div className={cn('relative overflow-hidden', className)}>
      <div
        ref={containerRef}
        role="region"
        aria-label="Route map"
        className="absolute inset-0"
      />
      {!ready && <Skeleton className="absolute inset-0 rounded-none" />}
      {children}
    </div>
  )
}
