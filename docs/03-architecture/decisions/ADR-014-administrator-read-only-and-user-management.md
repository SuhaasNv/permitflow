# ADR-014: The administrator reads every case and writes only users

Date: 21 September 2026. Stories: US-070, US-072, US-073 (FR-029, FR-030, SEC-003). Status: accepted, built.

## Context

The brief names two personas. The product decision (SCOPE.md, S7) added a third, the administrator, for oversight: is anything stuck, are the checks working, who has access. The brief's acceptance criteria say operators must never see internal status codes and every status change must be an officer's; an administrator who could also act on cases would blur that line and double the authorization surface. The owner also asked, on 21 September, for accounts to be created from the page rather than only by script.

## Options Considered

1. A separate administrator API and screens for cases (own read models, own routes).
2. The officer's read routes and screens, with the administrator admitted as a viewer whose actions are empty by construction, and user management as the only administrator write.
3. An administrator with full officer powers plus user management (a super-role).

## Decision

Option 2. `OfficerViewService.build()` takes the viewer and derives the actor from the role (`actor_for_role(admin)` is `None`), so an administrator's `actions[]` is empty and the frontend renders no control; the read routes (queue, case, audit trail, checklist, compare, the two downloads) admit the administrator through `OfficerOrAdmin` and `AnyReader`; every mutation keeps `OfficerUser`, and `feedback-templates` and the licence preview stay officer-only. The frontend reuses the officer screens under a `ReadOnlyProvider` context on `/admin/applications/:id` and the checklist route, with a banner and the officer's wording turned to the third person. User management is the one administrator write: `AdminUserService` locks the admin rows `FOR UPDATE ... ORDER BY id`, refuses the last active admin, the caller's own row and the protected demonstration accounts, translates a deadlock to `try_again`, and audits every change with no application. Account creation exists on the page and on the command line, both with a 12-character minimum and the audit row `user.created`.

## Rationale

- One read model for a case means the administrator sees exactly what the officer sees, and a field added for the officer is visible to the administrator without a second change; the authorization test per endpoint stays one test.
- Empty actions by construction, not by a frontend flag: the server never offers an administrator a transition, so a forged request meets the same 403 the tests assert on every mutation.
- Locking the admin rows in id order is the smallest thing that keeps "never zero administrators" true under two concurrent changes; the test demotes two administrators at once and accepts one success or two refusals, never two successes.
- Protected accounts keep the published demonstration working for the next reviewer without a separate "demo mode".

## Consequences

- An administrator sees a draft checklist while the officer is still on site (read-only); acceptable for oversight, stated in T25.
- The route lock test names the two administrator writes; a third one fails the test until it is named and reviewed.
- The users page shows no "last active" column: sessions record `last_seen_at` (US-093), but the product decision of 19 September stands until an owner asks.
- Production would add MFA for administrators, a second administrator's approval for a promotion to `admin`, and an audit row per case an administrator opens (T19 gap).
