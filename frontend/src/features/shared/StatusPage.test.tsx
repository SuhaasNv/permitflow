import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import * as healthApi from '@/api/health'

import { StatusPage } from './StatusPage'

describe('StatusPage', () => {
  it('renders the API status from /health', async () => {
    vi.spyOn(healthApi, 'getHealth').mockResolvedValue({ status: 'ok', database: 'ok' })
    render(
      <AppProviders>
        <MemoryRouter>
          <StatusPage />
        </MemoryRouter>
      </AppProviders>,
    )
    await waitFor(() => expect(screen.getByTestId('api-status')).toHaveTextContent('ok'))
  })
})
