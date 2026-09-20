# PermitFlow: Frontend Architecture (as built)

Rewritten on 20 September 2026 from the tree in `frontend/src`. The design-phase version of this document described a plan (OpenAPI-generated types, a drawer navigation, admin pages); this one describes what shipped. `docs/03-architecture/ARCHITECTURE.md` "Frontend structure" is the short form; this is the long one.

## Stack

React 19, TypeScript strict (no `any`), Vite, Tailwind v4, TanStack Query, React Hook Form with Zod, React Router. Tests: vitest with Testing Library (160 tests in 33 files, coverage thresholds in `vite.config.ts`), Playwright (the journey, six scenarios, an axe accessibility gate over 23 screen states). Linting: oxlint.

## Tree

```
src/
  api/        typed client (client.ts: bearer header, error envelope to AppError, 429 message, network mapping),
              one module per resource (auth, applications, sections, documents, officer, notifications, formSchema);
              types are written by hand to mirror app/schemas and pinned by endpoints.test.ts against the API table
  app/        router.tsx (public routes, /app/* operator, /officer/*, /admin/overview; role guards via RequireRole),
              providers.tsx (QueryClient, Auth), AppShell.tsx (side rail, bottom tab bar on phones, notifications bell)
  features/
    auth/     LoginPage, AuthContext (session in sessionStorage, expiry warning), RequireRole
    landing/  public landing page
    legal/    /privacy, /terms, /cookies rendered from content.ts
    operator/ DashboardPage, ApplicationsPage, ApplicationPage, FormPage + SectionForm, DocumentsPage + documents/
              (DropZone, DocumentSlot, VerificationBlock), ReviewPage, SubmittedPage, HistoryPage, FeedbackNotice,
              CompletionCard, Stepper; queries.ts (operator query keys and mutations), respond.ts (flagged-items walk)
    officer/  QueuePage, CasePage (sections, documents, CheckResult, FeedbackPanel, ComparePanel, AuditTrail),
              LicencePreviewPage; queries.ts (officer query keys and mutations)
    admin/    OverviewPage placeholder (the admin epic is v0.4.0)
    shared/   StatusBadge, Alert, Toast, Dialog (native <dialog>), Button, Field, Controls, PageHeader, Breadcrumb,
              SearchBox, SaveIndicator, Reveal, Logo, NotificationsBell, states (Skeleton, EmptyState, ErrorPanel, NotFoundPanel)
  lib/        zodFromSchema (Zod schemas built from GET /form-schema), format, search, session, unsaved, cn
  styles/     index.css (design tokens as CSS variables, Tailwind theme), fonts.css (self-hosted fonts)
  test/       vitest setup and fixtures
```

## Data flow

- Server state lives in TanStack Query. Query keys are per resource (`['operator','application',id]`, `['officer','case',id]`, `['officer','audit',id]`, `['officer','queue']`, `['form-schema']`). Mutations write the returned view into the case or application key and invalidate the lists and the audit trail that the change affects (`officer/queries.ts` `afterCaseChange`).
- Polling: the operator application and the officer case refetch every 2 s while any document check is `pending` or `running`, only while the tab is visible, and stop after a check is older than three minutes (`isCheckStale`, shared by both roles; the operator slot wakes itself when the window closes so it can offer Re-run without a navigation). The queue refetches every 30 s; the notifications bell every 30 s.
- Forms: React Hook Form with a Zod resolver built at runtime from the server's form schema (`lib/zodFromSchema.ts`), so the client validates the same rules the server enforces; server 422 details are mapped back onto fields.
- Labels and status: every status label, tone and available action comes from the API for the caller's role. Operator components never receive an internal status code; officer components render the officer label and the server-derived `available_actions` with their disabled reasons.
- Verification display: the operator sees the server's run status (`pending`, `running`, then a terminal state), the summary and the issues; nothing about the check is simulated on the client.

## Errors and states

`api/client.ts` turns every non-2xx into `AppError { code, message, details, requestId }` and maps a failed fetch to a network error. A query that fails on its first load renders `ErrorPanel` with the request id and a retry, while a failed background refetch keeps the cached view and any unsaved input (a poll that meets a 429 must not wipe the form); mutation errors render an inline `Alert` and keep the user's input; 429 shows the server message; unknown routes render `NotFoundPanel`. Loading uses skeletons. There is no React error boundary for render crashes (recorded in the readiness review).

## Security on the client

The JWT is held in `sessionStorage` (per tab, cleared on close) and sent as a bearer header; this is an accepted demonstration choice, an httpOnly cookie with CSRF protection is the production choice (readiness review row 3). No `dangerouslySetInnerHTML`; the served Content Security Policy allows scripts from self only.

## Accessibility and layout

Native `<dialog>`, labelled controls, landmarks per page, a skip link, status shown as label plus dot, focus-visible styles. Layouts are verified at 390, 1024 and 1280 by hand and by the axe gate (desktop and 390). Navigation: side rail on desktop, bottom tab bar under `md`.

## Known gaps

Two screens compute "flagged items changed" differently (`FormPage` counts documents as one item, `ApplicationPage` per document type); `ApplicationRow` and `ApplicationPage` branch on the label or tone string to bucket applications, where a server-provided phase would be safer; the feedback "Go to" anchor does not scroll on a cold load of the documents page; `FeedbackPanel` keeps a client-side list of statuses in which resolve is allowed. Each is in `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md` after the 20 September review.
