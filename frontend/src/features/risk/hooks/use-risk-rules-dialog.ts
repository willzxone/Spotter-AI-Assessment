import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { ConditionKind, RiskLevelName } from '@/integrations/rpc/api.gen'
import { errorMessage } from '@/integrations/rpc/client'
import { riskRulesQueryOptions } from '../api/queries'
import { CONDITIONS, RISK_ORDER } from '../constants'
import { describeBand } from '../utils/describe-band'

export interface ConditionRow {
  kind: ConditionKind
  label: string
  unit: string
  /** One range per level, in `RISK_ORDER`. */
  ranges: { level: RiskLevelName; text: string }[]
}

export function useRiskRulesDialog() {
  const [open, setOpen] = useState(false)
  // Fetched on first open; the rules never change while the app is running.
  const query = useQuery({ ...riskRulesQueryOptions(), enabled: open })

  const rows: ConditionRow[] = (query.data?.conditions ?? []).map(
    (condition) => {
      const { label, decimals } = CONDITIONS[condition.kind]
      return {
        kind: condition.kind,
        label,
        unit: condition.unit,
        ranges: RISK_ORDER.map((level) => {
          const band = condition.bands.find((b) => b.level === level)
          return { level, text: band ? describeBand(band, decimals) : '–' }
        }),
      }
    },
  )

  return {
    open,
    setOpen,
    rows,
    loadRules: query.data?.loadRules ?? [],
    isPending: query.isPending,
    error: query.isError ? errorMessage(query.error) : null,
    retry: () => void query.refetch(),
  }
}
