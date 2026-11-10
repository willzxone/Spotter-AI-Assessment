import { useForm, useStore } from '@tanstack/react-form'
import { useState } from 'react'
import type { FormEvent } from 'react'
import type { PlanInput } from '@/integrations/rpc/api.gen'
import { CHECKPOINT_INTERVALS_MI } from '../constants'
import { toDateTimeLocal } from '../utils/format'
import {
  defaultTripValues,
  departureWindow,
  toPlanInput,
  tripFormSchema,
} from '../utils/trip-form'

interface FieldMetaLike {
  isTouched: boolean
  errors: readonly unknown[]
}

/** A field error is a string from a field validator or an issue from the schema. */
function messageOf(error: unknown): string | undefined {
  if (typeof error === 'string') return error
  if (
    error &&
    typeof error === 'object' &&
    'message' in error &&
    typeof error.message === 'string'
  ) {
    return error.message
  }
  return undefined
}

export function useTripForm({
  onPlan,
}: {
  onPlan: (input: PlanInput) => void
}) {
  // Computed once: recomputing on render would move the default under the user.
  const [defaultValues] = useState(defaultTripValues)

  const form = useForm({
    defaultValues,
    validators: { onChange: tripFormSchema },
    onSubmit: ({ value }) => onPlan(toPlanInput(value)),
  })

  const submitted = useStore(form.store, (s) => s.submissionAttempts > 0)

  /** The field's first error, once the user has touched it or tried to submit. */
  function errorOf(meta: FieldMetaLike): string | undefined {
    if (!meta.isTouched && !submitted) return undefined
    for (const error of meta.errors) {
      const message = messageOf(error)
      if (message) return message
    }
    return undefined
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void form.handleSubmit()
  }

  function swapPlaces() {
    const { origin, destination } = form.state.values
    form.setFieldValue('origin', destination)
    form.setFieldValue('destination', origin)
  }

  function setDepartureNow() {
    form.setFieldValue('departure', toDateTimeLocal(new Date()))
  }

  function selectInterval(value: string) {
    const interval = CHECKPOINT_INTERVALS_MI.find((i) => String(i) === value)
    // A single toggle group reports '' when the active item is clicked again; keep the choice.
    if (interval) form.setFieldValue('intervalMi', interval)
  }

  const { earliest, latest } = departureWindow()

  return {
    form,
    errorOf,
    handleSubmit,
    swapPlaces,
    setDepartureNow,
    selectInterval,
    departureMin: toDateTimeLocal(new Date(earliest)),
    departureMax: toDateTimeLocal(new Date(latest)),
  }
}
