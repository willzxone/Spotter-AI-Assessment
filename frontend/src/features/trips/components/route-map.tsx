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
      {/* MapLibre's stylesheet gives its container `position: relative`, and as unlayered
          CSS it beats Tailwind's utilities, so the container must not rely on `absolute`
          for its size: the wrapper is positioned, the map element only fills it. */}
      <div className="absolute inset-0">
        <div
          ref={containerRef}
          role="region"
          aria-label="Route map"
          className="size-full"
        />
      </div>
      {!ready && <Skeleton className="absolute inset-0 rounded-none" />}
      {children}
    </div>
  )
}
