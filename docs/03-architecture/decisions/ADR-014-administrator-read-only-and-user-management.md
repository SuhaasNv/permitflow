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

## Amended for v0.5.0 (US-101), 9 October 2026: the administrator also writes platform settings, inside the environment's bounds

Status of the amendment: accepted, backend built on `feat/us-101-platform-settings`; the settings screens follow once their artboards are approved. The decision above stands: the administrator is read-only on applications, `actions[]` stays empty, the state machine's authorisation table is unchanged. What changes is the list of things an administrator may write: users (US-073) and now **platform settings**, so the owner can respond to load or abuse without a redeploy.

### Context

Every limit (request rate, sign-in attempts, AI checks per person and per platform per day, drafts per person, upload size, the AI text cap) was an environment variable, so tightening one meant a redeploy. A control an administrator can change from a browser is also a control a thief of an administrator session can change, so the question is how much power that panel gets (T19, T14, ADR-012).

### Options considered

1. **Keep limits in the environment only.** Safest, and the status quo. A change needs a redeploy and access to Railway, which is too slow in an incident.
2. **A settings table that replaces the environment.** Simple, but a stolen session could set every limit to "unlimited" and the cost brake is gone. The environment would stop being a safety net.
3. **A settings table whose values are bounded by the environment (chosen).** The variable is the default and the ceiling; the panel moves a value only inside `[minimum, ceiling]`. A stolen session can lower a limit (a nuisance, visible, reversible) but cannot raise or remove one.
4. **History: a history table or the audit trail.** A table would duplicate what the append-only audit trail already records (actor, old value, new value, reason, time) and would need its own protection against edits. Chosen: the audit trail (`settings.changed`, `settings.reverted`, `application_id` null). `platform_settings` holds only the current override; no row means "follow the environment".

### Decision

- **Where it lives.** `domain/platform_settings.py` (pure) defines each setting: key, type, label, group, the environment field that is its default and ceiling, a minimum, an absolute cap (10 MB for uploads), and whether anything reads it yet. `services/platform_settings.py` has `LiveSettings`, the read side, and `PlatformSettingsService`, the administrator side. `models/platform_setting.py` and migration 0015 add the table (`key` PK, JSON `value`, `updated_by`, `updated_at`, `reason`).
- **Bounds.** A number must be a whole number in `[minimum, ceiling]`; the minimum is at least 1, so a limit cannot be switched off; where the environment is 0 (no limit) the ceiling is the absolute cap and the default stays "no limit" until a value is set. Out of bounds is 422 naming the bound. The scanner fail mode cannot be `open` when `APP_ENV=production`. The same rules run again when a value is read (a value above a ceiling lowered since is clamped, an invalid row is ignored), so a database edit cannot loosen a limit.
- **Reads.** Every consumer reads `live()`, which caches the table for 10 seconds with an injectable clock, falls back to the environment value for a key with no row, and never waits for the database: when the snapshot is due the caller is handed the current one (the environment values only before the first load) and one background daemon thread reloads it, on a private connection with a 3 second connect timeout and a 1 second statement timeout. A failed read keeps the last good snapshot (environment values only before the first load) and tries again after 10 seconds. A write bumps a generation counter, so a reload that began before it can never store its older rows as fresh. Consumers: the request limiter and the sign-in window (`build_request_limiter` in `main.py`, read on each hit), the draft and AI quotas (`services/quotas.py`), the upload gate and the body-limit middleware, the AI text cap (`services/verification.py`) and the overview's quota figure. An empty table is today's behaviour by construction.
- **Writes.** `GET /admin/settings`, `GET /admin/settings/history`, `PUT /admin/settings/{key}`, `POST /admin/settings/history/{event_id}/revert`, admin only. A change needs a reason (3 to 280 characters) and the administrator's own password again (step-up): a wrong password is 403 `step_up_failed` and counts against the sign-in limiter, which answers 429 when full. A per-key advisory lock serialises writers, the override and its audit row (old value, new value, reason) commit together, then the local cache is dropped and a Telegram message is posted (a no-op without `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`). A revert restores the value a setting had before the chosen entry, checked against today's bounds, with the same step-up, reason and audit (`settings.reverted`).
- **The AI pause switch.** While on, `new_run` stores each new check as `unavailable` with the reason `ai_paused` before any provider is chosen, and `run_verification` stops a check that was already pending. Nothing reaches the provider, the document stays, the application can still be submitted (AI-006), the reason is served to the operator, and paused checks do not count toward the quotas. When the worker arrives (US-098) the switch should hold checks in the queue instead.
- **Stored for later stories.** Worker concurrency (US-098), the Telegram per-check message switch (US-100) and the scanner fail mode (US-099) are settable and audited now, reported with `in_use: false`.
- **The route lock test** names the two new writes beside the two user routes.

### Consequences

- The environment variables become ceilings. Raising one is still a redeploy, which is the point (OPERATIONS.md).
- The cache is per process, so with several API processes a change reaches each within 10 seconds, not at once; the process that took the change sees it immediately. Before the first load completes (the first moments after a restart; the API loads once at start-up) the environment values apply, which are the ceilings, so nothing is ever looser than the environment. A failed read keeps the last good snapshot and tries again after 10 seconds.
- The async request middleware reads the cache on the event-loop thread. It never blocks there: the reload runs in a background thread on its own two-connection pool, so a dead database or an exhausted application pool leaves the limits served from the last snapshot instead of freezing the loop (review finding, 9 Oct 2026).
- An administrator can still hurt availability (lower a limit, pause the AI). The controls are that it needs the password again, is audited, is announced on Telegram and is one click to undo from the history.
- `LOGIN_RATE_LIMIT_PER_MINUTE` (failed sign-ins) stays environment-only; the step-up's wrong passwords count against it.

### Review amendments (9 October 2026, `fix/us-101-review`)

- **Reads never block.** See Reads and Consequences above: the reload is a background thread on a private pool with a 3 second connect timeout and a 1 second statement timeout, and a generation counter discards a reload that began before a write. The write path refreshes the cache itself on its worker thread, so the process that took the change still serves it at once. The earlier text (a short blocking query on the event loop every ten seconds) is withdrawn.
- **Failed step-up is audited.** A wrong password on a change or a revert writes `settings.step_up_failed` (the key and the action, never the password) in its own transaction, besides counting against the sign-in limiter.
- **Step-up on user management.** `POST /admin/users` and `PATCH /admin/users/{id}` carry the administrator's own password (`admin_password`) and are checked like the settings routes (security audit F2); the failure is audited as `user.step_up_failed`. The create body already had `password` (the new account's), hence the distinct name.
- **An override equal to the default does not exist.** Setting a value equal to the environment default deletes the override row (audited as a change back to the default), and a revert or a change compares against the stored row as well as the value in force, so a row left holding the default can still be cleared from the panel.
- **The AI pause is a known gap until US-098.** While paused, each new check ends `unavailable` with the reason `ai_paused` rather than waiting; the application can still be submitted and the document needs a manual re-check once the AI is back. US-098 (the worker) should hold these in the queue instead. To make the cost visible, switching the AI back on records `ended_while_paused` (the number of checks stored `ai_paused` since it was switched on) in the audit row, the feed line and the Telegram message.
- **Types.** `domain/platform_settings.py` takes `int | None` environment values and `object` for untrusted input; no `Any`.

### Revisit when

A second administrator's approval is required for a loosening change (the T19 gap), settings need to be shared instantly across many processes (a notification channel instead of a TTL), or a setting needs a per-environment lock that the panel cannot touch.

Links: US-101 (`docs/05-planning/USER_STORIES.md`), T19 and T31 (`docs/06-security/THREAT_MODEL.md`), ADR-012 (the limits), ADR-008 (audit in the same transaction), `docs/09-operations/OPERATIONS.md`, `docs/13-observability/OBSERVABILITY.md` (5a).
