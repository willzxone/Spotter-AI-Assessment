import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RiskBadge } from '@/features/risk'
import type { CheckpointOut } from '@/integrations/rpc/api.gen'
import { useCheckpointTable } from '../hooks/use-checkpoint-table'
import { formatEta, readingOf } from '../utils/format'
import { ReadingCell } from './reading-cell'

interface Props {
  checkpoints: CheckpointOut[]
  inspected: number | null
  onInspect: (index: number) => void
}

export function CheckpointTable({ checkpoints, inspected, onInspect }: Props) {
  const { rowRef } = useCheckpointTable(inspected)
  return (
    <Table>
      <TableHeader className="bg-background sticky top-0 z-10">
        <TableRow>
          <TableHead className="w-20">Mile</TableHead>
          <TableHead>ETA</TableHead>
          <TableHead>Risk</TableHead>
          <TableHead>Wind</TableHead>
          <TableHead>Gust</TableHead>
          <TableHead>Rain</TableHead>
          <TableHead>Snow</TableHead>
          <TableHead>Why</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {checkpoints.map((cp) => (
          <TableRow
            key={cp.index}
            ref={rowRef(cp.index)}
            data-state={cp.index === inspected ? 'selected' : undefined}
            onClick={() => onInspect(cp.index)}
            className="cursor-pointer"
          >
            <TableCell>
              {/* The row handles the click; the button makes it reachable by keyboard. */}
              <button
                type="button"
                className="font-medium tabular-nums underline-offset-2 hover:underline focus-visible:underline focus-visible:outline-none"
                aria-label={`Show checkpoint at mile ${Math.round(cp.mile)} on the map`}
              >
                {Math.round(cp.mile).toLocaleString()}
              </button>
            </TableCell>
            <TableCell className="tabular-nums">{formatEta(cp.eta)}</TableCell>
            <TableCell>
              <RiskBadge level={cp.level} />
            </TableCell>
            <ReadingCell reading={readingOf(cp, 'wind')} />
            <TableCell className="text-muted-foreground tabular-nums">
              {Math.round(cp.gustMph)} mph
            </TableCell>
            <ReadingCell reading={readingOf(cp, 'rain')} />
            <ReadingCell reading={readingOf(cp, 'snow')} />
            <TableCell className="text-muted-foreground max-w-80 text-xs whitespace-normal">
              {cp.drivers.length === 0
                ? 'Clear'
                : cp.drivers.map((d) => d.detail).join('; ')}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
