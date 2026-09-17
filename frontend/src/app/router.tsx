import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { LoginPage } from '@/features/auth/LoginPage'
import { LandingPage } from '@/features/landing/LandingPage'
import { RequireRole } from '@/features/auth/RequireRole'
import { AdminOverviewPage } from '@/features/admin/OverviewPage'
import { OfficerQueuePage } from '@/features/officer/QueuePage'
import { ApplicationPage } from '@/features/operator/ApplicationPage'
import { DocumentsPage } from '@/features/operator/DocumentsPage'
import { FormPage } from '@/features/operator/FormPage'
import { OperatorDashboardPage } from '@/features/operator/DashboardPage'
import { NotFoundPanel } from '@/features/shared/states'

export const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireRole roles={['operator']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/app/dashboard', element: <OperatorDashboardPage /> },
          { path: '/app/applications', element: <OperatorDashboardPage /> },
          { path: '/app/applications/:id', element: <ApplicationPage /> },
          { path: '/app/applications/:id/documents', element: <DocumentsPage /> },
          { path: '/app/applications/:id/form', element: <FormPage /> },
          {
            path: '/app/applications/:id/form/:sectionKey',
            element: <FormPage />,
          },
        ],
      },
    ],
  },
  {
    element: <RequireRole roles={['officer']} />,
    children: [
      {
        element: <AppShell />,
        children: [{ path: '/officer/queue', element: <OfficerQueuePage /> }],
      },
    ],
  },
  {
    element: <RequireRole roles={['admin']} />,
    children: [
      {
        element: <AppShell />,
        children: [{ path: '/admin/overview', element: <AdminOverviewPage /> }],
      },
    ],
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
