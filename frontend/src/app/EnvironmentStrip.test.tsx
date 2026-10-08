import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Health } from '@/api/health'
import * as healthApi from '@/api/health'
import { EnvironmentStrip } from './EnvironmentStrip'

function health(environment: Health['environment']): Health {
  return { status: 'ok', database: 'ok', version: '0.4.0', commit: 'abc1234', environment }
}

function renderStrip() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <EnvironmentStrip />
    </QueryClientProvider>,
  )
}

describe('EnvironmentStrip (US-109)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('says this is not the live service when the API reports development', async () => {
    vi.spyOn(healthApi, 'getHealth').mockResolvedValue(health('development'))
    renderStrip()
    const strip = await screen.findByRole('region', { name: 'Environment notice' })
    expect(strip).toHaveTextContent('Development environment: test data only, not the live service')
  })

  it('shows for any environment other than production', async () => {
    vi.spyOn(healthApi, 'getHealth').mockResolvedValue(health('test'))
    renderStrip()
    expect(await screen.findByRole('region', { name: 'Environment notice' })).toBeInTheDocument()
  })

  it('shows nothing in production', async () => {
    const spy = vi.spyOn(healthApi, 'getHealth').mockResolvedValue(health('production'))
    renderStrip()
    await vi.waitFor(() => expect(spy).toHaveBeenCalled())
    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(screen.queryByRole('region', { name: 'Environment notice' })).not.toBeInTheDocument()
  })

  it('shows nothing while health is loading', () => {
    vi.spyOn(healthApi, 'getHealth').mockReturnValue(new Promise<Health>(() => undefined))
    renderStrip()
    expect(screen.queryByRole('region', { name: 'Environment notice' })).not.toBeInTheDocument()
  })

  it('shows nothing when health fails', async () => {
    const spy = vi.spyOn(healthApi, 'getHealth').mockRejectedValue(new Error('down'))
    renderStrip()
    await vi.waitFor(() => expect(spy).toHaveBeenCalled())
    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(screen.queryByRole('region', { name: 'Environment notice' })).not.toBeInTheDocument()
  })
})
