import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { homeFor, useAuth } from '@/features/auth/AuthContext'
import { LoginPage } from '@/features/auth/LoginPage'
import { RequireRole } from '@/features/auth/RequireRole'
import { AdminOverviewPage } from '@/features/admin/OverviewPage'
import { OfficerQueuePage } from '@/features/officer/QueuePage'
import { OperatorDashboardPage } from '@/features/operator/DashboardPage'
import { NotFoundPanel } from '@/features/shared/states'

function Root() {
  const { user, ready } = useAuth()
  if (!ready) return null
  return <Navigate to={user ? homeFor(user.role) : '/login'} replace />
}

export const router = createBrowserRouter([
  { path: '/', element: <Root /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireRole roles={['operator']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/app/dashboard', element: <OperatorDashboardPage /> },
          { path: '/app/applications', element: <OperatorDashboardPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireRole roles={['officer']} />,
    children: [{ element: <AppShell />, children: [{ path: '/officer/queue', element: <OfficerQueuePage /> }] }],
  },
  {
    element: <RequireRole roles={['admin']} />,
    children: [{ element: <AppShell />, children: [{ path: '/admin/overview', element: <AdminOverviewPage /> }] }],
  },
  {
    path: '*',
    element: (
      <div className="mx-auto max-w-lg px-4 py-10">
        <NotFoundPanel backTo="/" backLabel="Back to PermitFlow" />
      </div>
    ),
  },
])
