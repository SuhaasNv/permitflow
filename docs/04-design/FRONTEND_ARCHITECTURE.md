# PermitFlow: frontend architecture for the design

Stack (unchanged from ADR-009): React 18, TypeScript strict, Vite, Tailwind, TanStack Query, React Hook Form, Zod. This document says how that stack implements the screens in `SCREEN_INVENTORY.md` against the API in `docs/03-architecture/ARCHITECTURE.md`.

## Folder layout

```
frontend/src
  api/            OpenAPI-generated types (openapi-typescript) + client.ts (fetch, bearer, error mapping to AppError)
  app/            router.tsx (role-guarded routes), providers.tsx (QueryClient, Auth), AppShell/, theme.css (tokens)
  features/
    auth/         LoginPage, useAuth (token in memory + sessionStorage), RequireRole
    landing/      LandingPage (public)
    operator/     DashboardPage, ApplicationFormPage, DocumentsPage, ReviewSubmitPage, SubmittedPage, ApplicationPage (respond), HistoryPage
    officer/      QueuePage, ReviewPage (handles both first review and resubmission variant), ComparePage, HistoryPage, dialogs/
    admin/        OverviewPage, UsersPage (+ AddUserDrawer, ChangeRoleDialog)
    notifications/ NotificationsPanel, useNotifications
    shared/       every component in COMPONENT_INVENTORY.md
  domain/         statusLabels.ts (mirror of the label table, used only for officer views), verification.ts (state → title/icon/tint), feedback.ts
  lib/            zodFromSchema.ts, format.ts (dates "17 Sep, 10:31", sizes), cn.ts
  styles/         tailwind.css
```

Principle: server state lives in TanStack Query; UI state (open drawer, collapsed nav, active tab) in component state or the URL; auth in one context. No global store is needed.

## Routing and guards

| Route | Role | Notes |
|-------|------|-------|
| `/` | public | landing |
| `/login` | public | redirects to the role home if already authenticated |
| `/app/*` | operator | |
| `/officer/*` | officer | admin can open `/officer/applications/:id` read-only via `/admin/applications/:id` (same page component, `readOnly` prop) |
| `/admin/*` | admin | |

`RequireRole` reads the role from the JWT claim and renders "Not available for your role" on mismatch; the server still enforces (SEC-001/003).

## Query keys and invalidation

```
['me']
['applications']                          operator list
['application', id]                       operator or officer view (role decides endpoint)
['application', id, 'revisions']
['application', id, 'compare', from, to]
['application', id, 'audit']
['officer', 'queue', filters]
['notifications']
['form-schema'], ['feedback-templates']
['admin', 'overview'], ['admin', 'ai-health'], ['admin', 'audit-feed'], ['admin', 'users']
```

- Polling: `['application', id]` uses `refetchInterval: 2000` while any document's latest run is `pending` or `running`; stops otherwise (FR-005).
- After any mutation on an application: invalidate `['application', id]`, `['applications']`, `['officer','queue']`, `['notifications']`; after resolve/withdraw feedback also `['application', id, 'audit']`.
- Optimistic updates only for `mark read` on notifications and `mark resolved` (rollback on error); every other mutation waits for the server (status changes must reflect the authoritative state machine).
- `expected_version` is read from the last `['application', id]` data and sent with officer transitions; a 409 `version_conflict` renders the reload banner (REL-007).

## Forms

- `GET /form-schema` → `zodFromSchema()` builds one Zod object per section; RHF `useForm` per section (each section saves independently, matching `PATCH /sections/{key}`).
- Validation on blur and on save; error summary at the top of the section lists failing fields with anchors; inline errors use `role="alert"`.
- Unsaved-change protection: `useBlocker` on dirty sections; the "Unsaved changes" dialog.
- During resubmission the schema is the same but `editableTargets` from the API decides which sections mount as forms and which as `KeyValueList`; a 403 from the server on a non-flagged section is shown as "This section is not open for changes" (defence in depth, the UI never offers it).

## Uploads

- `DropZone` validates extension, MIME and size client-side before the request (same rules as the server); shows the server message on 400.
- Upload uses `XMLHttpRequest` (for progress) or `fetch` with a `ReadableStream` when available; progress drives the card's upload bar.
- Duplicate detection is server-side by `sha256` (DOMAIN_MODEL Document); the client shows the returned "unchanged" flag as an info line.
- After 201 the card enters `pending` and polling starts.

## Feedback anchors (UX-004)

Each section and document slot renders with `id="section-<key>"` / `id="doc-<type>"`. `FeedbackItem`'s "Go to" calls `scrollIntoView({block:'start'})` and toggles a one-shot `highlight` class (1.6 s pulse). Keyboard users get the same via the link's `href="#..."`.

## Role-specific rendering

- Operator pages consume `ApplicationOperatorView` (label only). `StatusBadge` for operators takes the label string; it never maps codes.
- Officer pages consume `ApplicationOfficerView` (code + officer label); `TransitionActions` reads the allowed targets from the response, not from a client copy of the table, so the UI can never offer a transition the server rejects.

## Navigation shell

- `AppShell` holds `navCollapsed` in `localStorage`; collapsed rail is 64 px icons with `title` tooltips; the hamburger in the top bar toggles it and is the only control on phones (drawer overlay ≤ 768 px).
- Breakpoints: ≥ 1280 full; 1024–1279 rails narrow (content-first, feedback rail moves below the content); 768–1023 nav collapsed by default, tables get horizontal scroll, two-column forms become one; ≤ 767 bottom tab bar for operators, stacked cards, sticky primary action. Officer review and compare are desktop-first and remain usable at 1024 with the rail below.

## Motion

Tailwind `transition` utilities for hover/focus; `@keyframes` for spinner, indeterminate bar, shimmer and highlight pulse in `theme.css`; all wrapped by a `prefers-reduced-motion` media query that sets durations to 0.001 s. Route changes use a 350 ms opacity fade on the main region only.

## Accessibility implementation

Radix-style primitives are not required; native `dialog` (with focus trap polyfill) and `details` are sufficient. Every icon-only button has `aria-label`; live regions: verification blocks use `aria-live="polite"` so a state change is announced; toasts use `role="status"`.

## Testing hooks

`data-testid` on: status badge, feedback item, document card + verification state, transition buttons, resubmit button, compare rows. The Playwright critical journey (US-005) drives the flow in `UI_FLOW.md` using these ids.

## Known risks

- The design assumes the officer view returns `changed_sections` and `changed_document_types` for the current revision (used by S-23 markers). ARCHITECTURE.md describes the officer view generically; add these two fields when US-027 is built.
- Admin user management (S-41) needs `POST /admin/users`, `PATCH /admin/users/{id}` (role, is_active) which are added to ARCHITECTURE.md in this phase.
