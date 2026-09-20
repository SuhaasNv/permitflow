import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { LoginPage } from '@/features/auth/LoginPage'
import { LandingPage } from '@/features/landing/LandingPage'
import { PolicyPage } from '@/features/legal/PolicyPage'
import { RequireRole } from '@/features/auth/RequireRole'
import { AdminOverviewPage } from '@/features/admin/OverviewPage'
import { OfficerQueuePage } from '@/features/officer/QueuePage'
import { OfficerCasePage } from '@/features/officer/CasePage'
import { ChecklistPage } from '@/features/officer/ChecklistPage'
import { LicencePreviewPage } from '@/features/officer/LicencePreviewPage'
import { ApplicationPage } from '@/features/operator/ApplicationPage'
import { DocumentsPage } from '@/features/operator/DocumentsPage'
import { FormPage } from '@/features/operator/FormPage'
import { ReviewPage } from '@/features/operator/ReviewPage'
import { SubmittedPage } from '@/features/operator/SubmittedPage'
import { ClarificationPage } from '@/features/operator/ClarificationPage'
import { HistoryPage } from '@/features/operator/HistoryPage'
import { OperatorDashboardPage } from '@/features/operator/DashboardPage'
import { ApplicationsPage } from '@/features/operator/ApplicationsPage'
import { NotFoundPanel } from '@/features/shared/states'

export const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/privacy', element: <PolicyPage /> },
  { path: '/terms', element: <PolicyPage /> },
  { path: '/cookies', element: <PolicyPage /> },
  {
    element: <RequireRole roles={['operator']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/app/dashboard', element: <OperatorDashboardPage /> },
          { path: '/app/applications', element: <ApplicationsPage /> },
          { path: '/app/applications/:id', element: <ApplicationPage /> },
          { path: '/app/applications/:id/documents', element: <DocumentsPage /> },
          { path: '/app/applications/:id/review', element: <ReviewPage /> },
          { path: '/app/applications/:id/submitted', element: <SubmittedPage /> },
          { path: '/app/applications/:id/history', element: <HistoryPage /> },
          { path: '/app/applications/:id/clarification', element: <ClarificationPage /> },
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
        children: [
          { path: '/officer/queue', element: <OfficerQueuePage /> },
          { path: '/officer/applications/:id', element: <OfficerCasePage /> },
          { path: '/officer/applications/:id/licence-preview', element: <LicencePreviewPage /> },
          { path: '/officer/applications/:id/checklist', element: <ChecklistPage /> },
        ],
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
        <NotFoundPanel
          backTo="/"
          backLabel="Back to PermitFlow"
          title="Page not found"
          description="There is nothing at this address. Check the link, or start from the front page."
        />
      </div>
    ),
  },
])
