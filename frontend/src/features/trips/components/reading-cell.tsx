import { TableCell } from '@/components/ui/table'
import { RISK_LEVELS } from '@/features/risk'
import type { Reading } from '../utils/format'

interface Props {
  reading: Reading
}

/** A condition's value, with a dot in the colour of the level it reaches on its own. */
export function ReadingCell({ reading }: Props) {
  const { label, color } = RISK_LEVELS[reading.level]
  return (
    <TableCell className="tabular-nums">
      <span className="inline-flex items-center gap-1.5">
        <span
          aria-hidden
          className="size-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        {reading.value}
        <span className="sr-only">({label})</span>
      </span>
    </TableCell>
  )
}
