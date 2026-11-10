import { useEffect, useEffectEvent, useState } from 'react'
import type { PlanOutput } from '@/integrations/rpc/api.gen'
import { PLAYBACK_STEP_MS } from '../constants'
import { heatmapHourOf, heatmapTime, truckPositionAt } from '../utils/progress'

/** What the user is looking at within one plan. */
interface View {
  plan: PlanOutput
  routeId: string
  hour: number
  inspected: number | null
  playing: boolean
}

function initialView(plan: PlanOutput): View {
  return {
    plan,
    routeId: plan.recommendedId,
    hour: 0,
    inspected: null,
    playing: false,
  }
}

/**
 * The selected route, the heatmap hour and the inspected checkpoint. The state
 * is tied to the plan it was made for, so a new plan starts fresh on its
 * recommended route without an effect resetting anything.
 */
export function usePlanView(plan: PlanOutput | null) {
  const [stored, setStored] = useState<View | null>(null)
  const view = plan
    ? stored?.plan === plan
      ? stored
      : initialView(plan)
    : null

  function update(patch: (current: View) => Partial<View>) {
    if (!plan) return
    setStored((prev) => {
      const base = prev?.plan === plan ? prev : initialView(plan)
      return { ...base, ...patch(base) }
    })
  }

  const route = plan?.routes.find((r) => r.id === view?.routeId) ?? null
  /** Best first, so the recommendation leads the list. */
  const rankedRoutes = plan
    ? [...plan.routes].sort((a, b) => a.rank - b.rank)
    : []
  const inspected =
    route?.checkpoints.find((cp) => cp.index === view?.inspected) ?? null
  const hour = view?.hour ?? 0
  const maxHour = plan?.heatmap.hours ?? 0
  const at = plan ? heatmapTime(plan.heatmap, hour) : null
  const truck =
    plan && route && at ? truckPositionAt(route, plan.departureAt, at) : null

  // Playback stops by itself on the last hour.
  const playing = (view?.playing ?? false) && hour < maxHour
  const step = useEffectEvent(() => {
    update((v) => ({ hour: Math.min(v.hour + 1, maxHour) }))
  })
  useEffect(() => {
    if (!playing) return
    const timer = setInterval(step, PLAYBACK_STEP_MS)
    return () => clearInterval(timer)
  }, [playing])

  return {
    route,
    rankedRoutes,
    inspected,
    hour,
    maxHour,
    at,
    truck,
    playing,
    selectRoute(id: string) {
      update(() => ({ routeId: id, inspected: null }))
    },
    /** Inspect a checkpoint and move the heatmap to when the truck gets there. */
    inspect(index: number) {
      if (!plan) return
      update((v) => {
        const cp = plan.routes
          .find((r) => r.id === v.routeId)
          ?.checkpoints.find((c) => c.index === index)
        if (!cp) return {}
        return {
          inspected: index,
          hour: heatmapHourOf(plan.heatmap, cp.eta),
          playing: false,
        }
      })
    },
    closeInspector() {
      update(() => ({ inspected: null }))
    },
    setHour(next: number) {
      update(() => ({ hour: next, playing: false }))
    },
    togglePlayback() {
      update((v) => {
        if (playing) return { playing: false }
        // From the last hour, play starts over.
        return { playing: true, hour: v.hour >= maxHour ? 0 : v.hour }
      })
    },
  }
}
