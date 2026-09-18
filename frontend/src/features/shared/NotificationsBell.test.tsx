import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/notifications'
import { AppProviders } from '@/app/providers'
import { NotificationsBell } from './NotificationsBell'

describe('NotificationsBell', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the unread count, lists items and marks one read when opened', async () => {
    vi.spyOn(api, 'getNotifications').mockResolvedValue({
      unread_count: 1,
      items: [
        {
          id: 'n1',
          application_id: 'a1',
          kind: 'status_changed',
          title: 'PF-2026-001005: Under Review',
          body: 'A licensing officer has started reviewing your application.',
          read_at: null,
          created_at: new Date().toISOString(),
        },
      ],
    })
    const read = vi.spyOn(api, 'markNotificationRead').mockResolvedValue({
      id: 'n1',
      application_id: 'a1',
      kind: 'status_changed',
      title: 't',
      body: 'b',
      read_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    })
    render(
      <AppProviders>
        <MemoryRouter>
          <NotificationsBell role="operator" />
        </MemoryRouter>
      </AppProviders>,
    )
    const bell = await screen.findByRole('button', { name: 'Notifications, 1 unread' })
    await userEvent.click(bell)
    const item = await screen.findByRole('button', { name: /PF-2026-001005: Under Review/ })
    expect(item).toBeInTheDocument()
    await userEvent.click(item)
    await waitFor(() => expect(read).toHaveBeenCalledWith('n1'))
  })
})
