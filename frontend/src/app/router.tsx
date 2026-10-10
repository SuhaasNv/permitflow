import type { ComponentType } from 'react'
import { Outlet, createBrowserRouter } from 'react-router-dom'

import { AppShell } from './AppShell'
import { EnvironmentStrip } from './EnvironmentStrip'
import { LoginPage } from '@/features/auth/LoginPage'
import { LandingPage } from '@/features/landing/LandingPage'
import { PolicyPage } from '@/features/legal/PolicyPage'
import { ReleasesPage } from '@/features/releases/ReleasesPage'
import { RequireRole } from '@/features/auth/RequireRole'
import { ReadOnlyProvider } from '@/features/officer/readOnly'
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
import { Skeleton } from '@/features/shared/states'
import { RouteTitle, titled } from './RouteTitle'

/** The officer and administrator screens load on first visit, so a sign-in or an operator's first paint does not carry them
 * (the 250 KB budget measures that first load: scripts/check-bundle-size.mjs). Between two screens the old one stays until the next is ready. */
function lazyPage<K extends string>(load: () => Promise<Record<K, ComponentType>>, name: K) {
  return { lazy: async () => ({ Component: (await load())[name] }) }
}

/** Shown while the first screen's code arrives, when the address opens straight on one of the lazy screens. */
function LoadingScreen() {
  return (
    <div className="mx-auto max-w-[1360px] px-4 py-8 sm:px-8" role="status" aria-busy="true" aria-label="Loading">
      <Skeleton className="mb-3 h-8 w-64" />
      <Skeleton className="h-4 w-96" />
    </div>
  )
}

/** The one root layout: the environment notice above every page (US-109), then the page under its tab title. */
function RootLayout() {
  return (
    <>
      <EnvironmentStrip />
      <RouteTitle />
    </>
  )
}

export const router = createBrowserRouter([
  {
    // Every screen names its browser tab through its route's handle (RouteTitle).
    element: <RootLayout />,
    hydrateFallbackElement: <LoadingScreen />,
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
              { path: '/officer/queue', ...lazyPage(() => import('@/features/officer/QueuePage'), 'OfficerQueuePage'), handle: titled('Review queue') },
              { path: '/officer/applications/:id', ...lazyPage(() => import('@/features/officer/CasePage'), 'OfficerCasePage'), handle: titled('Application review') },
              { path: '/officer/applications/:id/licence-preview', ...lazyPage(() => import('@/features/officer/LicencePreviewPage'), 'LicencePreviewPage'), handle: titled('Licence preview') },
              { path: '/officer/applications/:id/checklist', ...lazyPage(() => import('@/features/officer/ChecklistPage'), 'ChecklistPage'), handle: titled('Site visit checklist') },
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
              { path: '/admin/overview', ...lazyPage(() => import('@/features/admin/OverviewPage'), 'AdminOverviewPage'), handle: titled('Operations overview') },
              { path: '/admin/activity', ...lazyPage(() => import('@/features/admin/ActivityPage'), 'AdminActivityPage'), handle: titled('Activity') },
              { path: '/admin/users', ...lazyPage(() => import('@/features/admin/UsersPage'), 'AdminUsersPage'), handle: titled('Users') },
              { path: '/admin/settings', ...lazyPage(() => import('@/features/admin/SettingsPage'), 'AdminSettingsPage'), handle: titled('Settings') },
              // The officer screens, read-only (US-072): the server sends no actions, the components render no controls.
              {
                element: (
                  <ReadOnlyProvider value={true}>
                    <Outlet />
                  </ReadOnlyProvider>
                ),
                children: [
                  { path: '/admin/applications/:id', ...lazyPage(() => import('@/features/officer/CasePage'), 'OfficerCasePage'), handle: titled('Application (read-only)') },
                  { path: '/admin/applications/:id/checklist', ...lazyPage(() => import('@/features/officer/ChecklistPage'), 'ChecklistPage'), handle: titled('Site visit checklist (read-only)') },
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
