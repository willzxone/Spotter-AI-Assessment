import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RANKING_CRITERIA, RISK_ORDER } from '../constants'
import { useRiskRulesDialog } from '../hooks/use-risk-rules-dialog'
import { RiskBadge } from './risk-badge'

export function RiskRulesDialog() {
  const { open, setOpen, rows, loadRules, isPending, error, retry } =
    useRiskRulesDialog()

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          Risk rules
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>How risk is scored</DialogTitle>
          <DialogDescription>
            Each checkpoint takes the worst level across wind, rain, snow and
            the load rule. These thresholds come straight from the server.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <div className="flex items-center justify-between gap-4 text-sm">
            <p className="text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={retry}>
              Retry
            </Button>
          </div>
        ) : isPending ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Condition</TableHead>
                  {RISK_ORDER.map((level) => (
                    <TableHead key={level}>
                      <RiskBadge level={level} />
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.kind}>
                    <TableCell className="font-medium">
                      {row.label}{' '}
                      <span className="text-muted-foreground">
                        ({row.unit})
                      </span>
                    </TableCell>
                    {row.ranges.map((range) => (
                      <TableCell key={range.level} className="tabular-nums">
                        {range.text}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <section className="flex flex-col gap-2 text-sm">
              <h3 className="font-medium">Load rules</h3>
              <ul className="flex flex-col gap-1.5">
                {loadRules.map((rule) => (
                  <li key={rule.text} className="flex items-center gap-2">
                    <RiskBadge level={rule.level} />
                    {rule.text}
                  </li>
                ))}
              </ul>
            </section>

            <section className="flex flex-col gap-2 text-sm">
              <h3 className="font-medium">Choosing a route</h3>
              <ol className="text-muted-foreground list-inside list-decimal">
                {RANKING_CRITERIA.map((criterion) => (
                  <li key={criterion}>{criterion}</li>
                ))}
              </ol>
            </section>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
