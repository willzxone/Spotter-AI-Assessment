// @vitest-environment happy-dom
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CheckpointTable } from '@/features/trips/components/checkpoint-table'
import { PlanResults } from '@/features/trips/components/plan-results'
import { RouteCard } from '@/features/trips/components/route-card'
import { checkpoint, plan, route } from './fixtures/plan'

afterEach(cleanup)

const stormy = route({
  id: 'B',
  rank: 2,
  recommended: false,
  verdict: 'More Severe miles than Route A (15 mi vs 0 mi).',
  risk: {
    worst: 'severe',
    average: 1.2,
    miles: { low: 80, moderate: 0, high: 5, severe: 15, noTravel: 0 },
  },
})

describe('RouteCard', () => {
  it('states the risk in words, not only in colour', () => {
    render(<RouteCard route={stormy} selected={false} onSelect={vi.fn()} />)
    const card = screen.getByRole('button', { name: /Route B/ })

    expect(within(card).getByText('Severe')).toBeTruthy()
    expect(
      within(card).getByText('Low 80 mi · High 5 mi · Severe 15 mi'),
    ).toBeTruthy()
    expect(within(card).getByText(stormy.verdict)).toBeTruthy()
    expect(within(card).queryByText('Recommended')).toBeNull()
    expect(card.getAttribute('aria-pressed')).toBe('false')
  })

  it('selects its route when chosen', async () => {
    const onSelect = vi.fn()
    render(<RouteCard route={route()} selected onSelect={onSelect} />)
    const card = screen.getByRole('button', { name: /Route A/ })

    expect(within(card).getByText('Recommended')).toBeTruthy()
    expect(card.getAttribute('aria-pressed')).toBe('true')
    await userEvent.setup().click(card)
    expect(onSelect).toHaveBeenCalledWith('A')
  })
})

describe('PlanResults', () => {
  const base = {
    selectedId: null,
    isPlanning: false,
    isOutdated: false,
    error: null,
    onSelectRoute: vi.fn(),
  }

  it('explains what the planner does before the first trip', () => {
    render(<PlanResults {...base} plan={null} routes={[]} />)
    expect(screen.getByText(/compare up to three routes/)).toBeTruthy()
  })

  it("shows the server's reason when planning fails", () => {
    render(
      <PlanResults
        {...base}
        plan={null}
        routes={[]}
        error="No drivable route connects these places."
      />,
    )
    const alert = screen.getByRole('alert')
    expect(within(alert).getByText('Could not plan this trip')).toBeTruthy()
    expect(
      within(alert).getByText('No drivable route connects these places.'),
    ).toBeTruthy()
  })

  it('lists the routes in the order given and marks the selected one', () => {
    const p = plan({ routes: [route(), stormy] })
    render(<PlanResults {...base} plan={p} routes={p.routes} selectedId="B" />)
    const cards = screen
      .getAllByRole('button')
      .filter((b) => b.hasAttribute('aria-pressed'))
    expect(cards.map((c) => c.getAttribute('aria-pressed'))).toEqual([
      'false',
      'true',
    ])
    expect(screen.getByText('Routing: OSRM · Weather: Open-Meteo')).toBeTruthy()
    expect(screen.queryByText('Simulated data')).toBeNull()
  })

  it('says when routes or weather are simulated, and passes on warnings', () => {
    const p = plan({
      sources: { routing: 'simulated', weather: 'simulated' },
      warnings: ['Only 2 distinct routes were found.'],
    })
    render(<PlanResults {...base} plan={p} routes={p.routes} />)
    expect(screen.getByText('Simulated data')).toBeTruthy()
    expect(screen.getByText('Only 2 distinct routes were found.')).toBeTruthy()
  })
})

describe('CheckpointTable', () => {
  const checkpoints = [
    checkpoint(0, 0),
    checkpoint(1, 25, {
      level: 'severe',
      windLevel: 'severe',
      windMph: 47,
      drivers: [{ kind: 'wind', level: 'severe', detail: 'Wind 47 mph' }],
    }),
  ]

  it('says why a checkpoint is risky, and "Clear" when it is not', () => {
    render(
      <CheckpointTable
        checkpoints={checkpoints}
        inspected={null}
        onInspect={vi.fn()}
      />,
    )
    const [, clearRow, stormRow] = screen.getAllByRole('row')
    expect(within(clearRow!).getByText('Clear')).toBeTruthy()
    expect(within(stormRow!).getByText('Wind 47 mph')).toBeTruthy()
    // The level is in words for screen readers, beside the coloured dot.
    expect(within(stormRow!).getByText('(Severe)')).toBeTruthy()
  })

  it('inspects a checkpoint from the keyboard-reachable mile button', async () => {
    const onInspect = vi.fn()
    render(
      <CheckpointTable
        checkpoints={checkpoints}
        inspected={null}
        onInspect={onInspect}
      />,
    )
    await userEvent.setup().click(
      screen.getByRole('button', {
        name: 'Show checkpoint at mile 25 on the map',
      }),
    )
    expect(onInspect).toHaveBeenCalledExactlyOnceWith(1)
  })
})
