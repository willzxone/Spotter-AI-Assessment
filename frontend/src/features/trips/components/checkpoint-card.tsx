import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { RiskBadge } from '@/features/risk'
import type { CheckpointOut } from '@/integrations/rpc/api.gen'
import { formatDateTime, readings } from '../utils/format'

interface Props {
  checkpoint: CheckpointOut
  onClose: () => void
}

export function CheckpointCard({ checkpoint: cp, onClose }: Props) {
  return (
    <section
      aria-label={`Checkpoint at mile ${Math.round(cp.mile)}`}
      className="bg-background/95 flex w-72 flex-col gap-3 rounded-lg border p-3 text-sm shadow-md backdrop-blur"
    >
      <header className="flex items-start gap-2">
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="font-semibold">
            Mile {Math.round(cp.mile).toLocaleString()}
          </span>
          <span className="text-muted-foreground text-xs">
            Arrives {formatDateTime(cp.eta)} · +
            {cp.hoursFromDeparture.toFixed(1)} h
          </span>
        </div>
        <RiskBadge level={cp.level} />
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="-mt-1 -mr-1 size-7"
          onClick={onClose}
          aria-label="Close checkpoint details"
        >
          <X />
        </Button>
      </header>

      <dl className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1.5">
        {readings(cp).map((r) => (
          <div key={r.kind} className="contents">
            <dt className="text-muted-foreground">{r.label}</dt>
            <dd className="tabular-nums">
              {r.value}
              {r.kind === 'wind' && (
                <span className="text-muted-foreground">
                  {' '}
                  (gusts {Math.round(cp.gustMph)})
                </span>
              )}
            </dd>
            <dd>
              <RiskBadge level={r.level} />
            </dd>
          </div>
        ))}
      </dl>

      {cp.drivers.length > 0 && (
        <ul className="flex flex-col gap-1 border-t pt-2 text-xs">
          {cp.drivers.map((driver) => (
            <li key={driver.kind} className="flex items-start gap-2">
              <RiskBadge level={driver.level} className="shrink-0" />
              <span>{driver.detail}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="text-muted-foreground text-xs">
        Stands for miles {Math.round(cp.coversFromMi)}-
        {Math.round(cp.coversToMi)} of the route.
      </p>
    </section>
  )
}
