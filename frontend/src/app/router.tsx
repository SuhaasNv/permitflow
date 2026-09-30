import { Outlet, createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { LoginPage } from '@/features/auth/LoginPage'
import { LandingPage } from '@/features/landing/LandingPage'
import { PolicyPage } from '@/features/legal/PolicyPage'
import { ReleasesPage } from '@/features/releases/ReleasesPage'
import { RequireRole } from '@/features/auth/RequireRole'
import { AdminActivityPage } from '@/features/admin/ActivityPage'
import { AdminOverviewPage } from '@/features/admin/OverviewPage'
import { AdminUsersPage } from '@/features/admin/UsersPage'
import { ReadOnlyProvider } from '@/features/officer/readOnly'
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
import { NotFoundPage } from '@/features/shared/NotFoundPage'
import { RouteTitle, titled } from './RouteTitle'

export const router = createBrowserRouter([
  {
    // Every screen names its browser tab through its route's handle (RouteTitle).
    element: <RouteTitle />,
    children: [
      { path: '/', element: <LandingPage />, handle: titled('PermitFlow | Food Establishment Licence', true) },
      { path: '/login', element: <LoginPage />, handle: titled('Sign in') },
      { path: '/privacy', element: <PolicyPage />, handle: titled('Privacy policy') },
      { path: '/terms', element: <PolicyPage />, handle: titled('Terms') },
      { path: '/cookies', element: <PolicyPage />, handle: titled('Cookies') },
      { path: '/releases', element: <ReleasesPage />, handle: titled("What's new") },
      { path: '/releases/:version', element: <ReleasesPage />, handle: titled("What's new") },
      {
        element: <RequireRole roles={['operator']} />,
        children: [
          {
            element: <AppShell />,
            children: [
              { path: '/app/dashboard', element: <OperatorDashboardPage />, handle: titled('Dashboard') },
              { path: '/app/applications', element: <ApplicationsPage />, handle: titled('My applications') },
              { path: '/app/applications/:id', element: <ApplicationPage />, handle: titled('Application') },
              { path: '/app/applications/:id/documents', element: <DocumentsPage />, handle: titled('Documents') },
              { path: '/app/applications/:id/review', element: <ReviewPage />, handle: titled('Review and submit') },
              { path: '/app/applications/:id/submitted', element: <SubmittedPage />, handle: titled('Application submitted') },
              { path: '/app/applications/:id/history', element: <HistoryPage />, handle: titled('Application history') },
              { path: '/app/applications/:id/clarification', element: <ClarificationPage />, handle: titled('Clarification') },
              { path: '/app/applications/:id/form', element: <FormPage />, handle: titled('Application form') },
              {
                path: '/app/applications/:id/form/:sectionKey',
                element: <FormPage />,
                handle: titled('Application form'),
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
              { path: '/officer/queue', element: <OfficerQueuePage />, handle: titled('Review queue') },
              { path: '/officer/applications/:id', element: <OfficerCasePage />, handle: titled('Application review') },
              { path: '/officer/applications/:id/licence-preview', element: <LicencePreviewPage />, handle: titled('Licence preview') },
              { path: '/officer/applications/:id/checklist', element: <ChecklistPage />, handle: titled('Site visit checklist') },
            ],
          },
        ],
      },
      {
        element: <RequireRole roles={['admin']} />,
        children: [
          {
            element: <AppShell />,
            children: [
              { path: '/admin/overview', element: <AdminOverviewPage />, handle: titled('Operations overview') },
              { path: '/admin/activity', element: <AdminActivityPage />, handle: titled('Activity') },
              { path: '/admin/users', element: <AdminUsersPage />, handle: titled('Users') },
              // The officer screens, read-only (US-072): the server sends no actions, the components render no controls.
              {
                element: (
                  <ReadOnlyProvider value={true}>
                    <Outlet />
                  </ReadOnlyProvider>
                ),
                children: [
                  { path: '/admin/applications/:id', element: <OfficerCasePage />, handle: titled('Application (read-only)') },
                  { path: '/admin/applications/:id/checklist', element: <ChecklistPage />, handle: titled('Site visit checklist (read-only)') },
                ],
              },
            ],
          },
        ],
      },
      { path: '*', element: <NotFoundPage />, handle: titled('Page not found') },
    ],
  },
])
