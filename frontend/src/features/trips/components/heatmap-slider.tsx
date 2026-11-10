import { Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { RiskLegend } from '@/features/risk'
import { formatDateTime } from '../utils/format'
import { describeTruck } from '../utils/progress'
import type { TruckPosition } from '../utils/progress'

interface Props {
  hour: number
  maxHour: number
  at: Date
  routeId: string
  truck: TruckPosition | null
  playing: boolean
  onHourChange: (hour: number) => void
  onTogglePlayback: () => void
}

export function HeatmapSlider({
  hour,
  maxHour,
  at,
  routeId,
  truck,
  playing,
  onHourChange,
  onTogglePlayback,
}: Props) {
  return (
    <div className="bg-background/95 flex flex-col gap-2 rounded-lg border p-3 shadow-md backdrop-blur">
      <div className="flex items-center gap-3">
        <Button
          type="button"
          size="icon"
          variant="outline"
          onClick={onTogglePlayback}
          aria-label={playing ? 'Pause forecast' : 'Play forecast'}
        >
          {playing ? <Pause /> : <Play />}
        </Button>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="font-medium tabular-nums">
              {formatDateTime(at.toISOString())}
              <span className="text-muted-foreground font-normal">
                {' '}
                · +{hour} h
              </span>
            </span>
            <span className="text-muted-foreground truncate text-xs">
              {truck && describeTruck(routeId, truck)}
            </span>
          </div>
          <Slider
            min={0}
            max={maxHour}
            step={1}
            value={[hour]}
            onValueChange={([next]) => {
              if (next !== undefined) onHourChange(next)
            }}
            aria-label="Forecast hour"
          />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-muted-foreground text-xs">
          Weather risk, {maxHour}-hour forecast:
        </span>
        <RiskLegend className="flex-row flex-wrap gap-x-3" />
      </div>
    </div>
  )
}
