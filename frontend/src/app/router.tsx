import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { StatusPage } from '@/features/shared/StatusPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <AppShell>
        <StatusPage />
      </AppShell>
    ),
  },
])
