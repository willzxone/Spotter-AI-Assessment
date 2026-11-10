import { ArrowUpDown, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { PlaceSearch } from '@/features/places'
import type { PlanInput } from '@/integrations/rpc/api.gen'
import { CHECKPOINT_INTERVALS_MI, MAX_LOAD_LB } from '../constants'
import { useTripForm } from '../hooks/use-trip-form'
import { FieldError } from './field-error'

interface Props {
  onPlan: (input: PlanInput) => void
  isPlanning: boolean
}

export function TripForm({ onPlan, isPlanning }: Props) {
  const {
    form,
    errorOf,
    handleSubmit,
    swapPlaces,
    setDepartureNow,
    selectInterval,
    departureMin,
    departureMax,
  } = useTripForm({ onPlan })

  return (
    <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex items-end gap-2">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <form.Field name="origin">
            {(field) => (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="origin">Origin</Label>
                <PlaceSearch
                  id="origin"
                  value={field.state.value?.label ?? null}
                  placeholder="Where does the trip start?"
                  onSelect={field.handleChange}
                  onBlur={field.handleBlur}
                  invalid={!!errorOf(field.state.meta)}
                />
                <FieldError
                  id="origin-error"
                  message={errorOf(field.state.meta)}
                />
              </div>
            )}
          </form.Field>
          <form.Field name="destination">
            {(field) => (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="destination">Destination</Label>
                <PlaceSearch
                  id="destination"
                  value={field.state.value?.label ?? null}
                  placeholder="Where is it going?"
                  onSelect={field.handleChange}
                  onBlur={field.handleBlur}
                  invalid={!!errorOf(field.state.meta)}
                />
                <FieldError
                  id="destination-error"
                  message={errorOf(field.state.meta)}
                />
              </div>
            )}
          </form.Field>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="mb-0.5 self-center"
          onClick={swapPlaces}
          aria-label="Swap origin and destination"
        >
          <ArrowUpDown />
        </Button>
      </div>

      <form.Field name="departure">
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="departure">Departure</Label>
            <div className="flex gap-2">
              <Input
                id="departure"
                type="datetime-local"
                min={departureMin}
                max={departureMax}
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                aria-invalid={!!errorOf(field.state.meta)}
                aria-describedby="departure-error"
              />
              <Button type="button" variant="outline" onClick={setDepartureNow}>
                Now
              </Button>
            </div>
            <FieldError
              id="departure-error"
              message={errorOf(field.state.meta)}
            />
          </div>
        )}
      </form.Field>

      <form.Field name="loadLb">
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="loadLb">Load weight (lb)</Label>
            <Input
              id="loadLb"
              type="number"
              inputMode="numeric"
              min={0}
              max={MAX_LOAD_LB}
              step={500}
              value={Number.isNaN(field.state.value) ? '' : field.state.value}
              onChange={(e) => field.handleChange(e.target.valueAsNumber)}
              onBlur={field.handleBlur}
              aria-invalid={!!errorOf(field.state.meta)}
              aria-describedby="loadLb-error"
            />
            <FieldError id="loadLb-error" message={errorOf(field.state.meta)} />
          </div>
        )}
      </form.Field>

      <form.Field name="intervalMi">
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <Label id="interval-label">Sample weather every</Label>
            <ToggleGroup
              type="single"
              variant="outline"
              aria-labelledby="interval-label"
              value={String(field.state.value)}
              onValueChange={selectInterval}
              className="w-full"
            >
              {CHECKPOINT_INTERVALS_MI.map((interval) => (
                <ToggleGroupItem
                  key={interval}
                  value={String(interval)}
                  className="flex-1"
                >
                  {interval} mi
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        )}
      </form.Field>

      <Button type="submit" disabled={isPlanning}>
        {isPlanning && <Loader2 className="animate-spin" />}
        {isPlanning ? 'Planning routes…' : 'Plan routes'}
      </Button>
    </form>
  )
}
