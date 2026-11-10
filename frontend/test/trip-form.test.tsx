// @vitest-environment happy-dom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TripForm } from '@/features/trips/components/trip-form'
import type { Place, PlanInput } from '@/integrations/rpc/api.gen'

/**
 * The form is the one place a mistake costs the user a round trip, so it is
 * driven the way a person uses it: open a picker, type, choose a result, submit.
 * Only `fetch` is faked, standing in for the backend's `geocoding/search`.
 */

const PLACES: Place[] = [
  {
    id: 'sim-chicago',
    name: 'Chicago',
    label: 'Chicago, Illinois, United States',
    lat: 41.8781,
    lon: -87.6298,
    kind: 'city',
  },
  {
    id: 'sim-atlanta',
    name: 'Atlanta',
    label: 'Atlanta, Georgia, United States',
    lat: 33.749,
    lon: -84.388,
    kind: 'city',
  },
]

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init: RequestInit) => {
      const { query } = JSON.parse(String(init.body)) as { query: string }
      const places = PLACES.filter((p) =>
        p.name.toLowerCase().startsWith(query.toLowerCase()),
      )
      return Promise.resolve(
        new Response(JSON.stringify({ places }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    }),
  )
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function renderForm() {
  const onPlan = vi.fn<(input: PlanInput) => void>()
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <TripForm onPlan={onPlan} isPlanning={false} />
    </QueryClientProvider>,
  )
  return { onPlan, user: userEvent.setup() }
}

type User = ReturnType<typeof userEvent.setup>

async function pick(user: User, field: string, query: string, name: string) {
  await user.click(screen.getByRole('combobox', { name: field }))
  await user.type(
    screen.getByPlaceholderText('Search a city or address…'),
    query,
  )
  await user.click(
    await screen.findByRole('option', { name: new RegExp(name) }),
  )
}

describe('TripForm', () => {
  it('names every missing field and does not plan', async () => {
    const { onPlan, user } = renderForm()
    await user.click(screen.getByRole('button', { name: 'Plan routes' }))

    expect(
      await screen.findByText('Choose where the trip starts.'),
    ).toBeTruthy()
    expect(screen.getByText('Choose where the trip ends.')).toBeTruthy()
    expect(onPlan).not.toHaveBeenCalled()
  })

  it('plans the trip the user entered', async () => {
    const { onPlan, user } = renderForm()
    await pick(user, 'Origin', 'Chi', 'Chicago')
    await pick(user, 'Destination', 'Atl', 'Atlanta')

    const load = screen.getByLabelText('Load weight (lb)')
    await user.clear(load)
    await user.type(load, '42000')
    await user.click(screen.getByRole('radio', { name: '50 mi' }))
    await user.click(screen.getByRole('button', { name: 'Plan routes' }))

    expect(onPlan).toHaveBeenCalledTimes(1)
    const input = onPlan.mock.calls[0]![0]
    expect(input).toMatchObject({
      origin: { lat: 41.8781, lon: -87.6298, label: PLACES[0]!.label },
      destination: { lat: 33.749, lon: -84.388, label: PLACES[1]!.label },
      loadLb: 42_000,
      intervalMi: 50,
    })
    // The default departure is the next quarter hour.
    const lead = Date.parse(input.departureAt) - Date.now()
    expect(lead).toBeGreaterThan(-60_000)
    expect(lead).toBeLessThanOrEqual(15 * 60_000)
  })

  it('swaps origin and destination', async () => {
    const { onPlan, user } = renderForm()
    await pick(user, 'Origin', 'Chi', 'Chicago')
    await pick(user, 'Destination', 'Atl', 'Atlanta')
    await user.click(
      screen.getByRole('button', { name: 'Swap origin and destination' }),
    )
    await user.click(screen.getByRole('button', { name: 'Plan routes' }))

    const input = onPlan.mock.calls[0]![0]
    expect(input.origin.label).toBe(PLACES[1]!.label)
    expect(input.destination.label).toBe(PLACES[0]!.label)
  })

  it('refuses a trip that starts where it ends', async () => {
    const { onPlan, user } = renderForm()
    await pick(user, 'Origin', 'Chi', 'Chicago')
    await pick(user, 'Destination', 'Chi', 'Chicago')
    await user.click(screen.getByRole('button', { name: 'Plan routes' }))

    expect(
      await screen.findByText('Destination must differ from the origin.'),
    ).toBeTruthy()
    expect(onPlan).not.toHaveBeenCalled()
  })
})
