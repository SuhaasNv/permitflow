# ADR-012: Abuse limits: per-client windows in process, quotas in the database

Date: 19 September 2026. Story: US-058. Status: accepted, built.

## Context

The demonstration runs with published credentials and a live model provider. Four attacks were named by the owner: hammer the sign-in endpoint, fill the database with garbage, run up the model bill through the expensive endpoint, and scrape. Until this story only failed sign-ins were limited (SEC-010), and nothing bounded the number of drafts or model calls.

## Constraints

- One backend process per environment on Railway, no Redis, no edge rules on the platform's own proxy.
- The AI check is advisory (ADR-006): a blocked check must not block the application.
- Limits must be explainable to the person who hits them, in operator words, and must never leak internal state.
- The browser test suite signs in dozens of times from one address.

## Options Considered

### Option A: rely on the platform
Railway's proxy has no configurable rate limit on this plan; there is nothing to rely on.

### Option B: Redis-backed windows shared by all processes
Correct for a fleet; adds a service, a secret and an operational dependency to a one-process deployment, and does not answer the cost question by itself.

### Option C: sliding-minute windows per client in process, plus quotas counted in the database
Windows for what must be fast and is naturally per process (request rate, sign-in attempts); the database for what must be true across restarts and workers and is naturally slow (drafts held, model calls per day). Nothing new to run.

## Decision

Option C. `app/core/rate_limit.py` keeps two windows per client address (every request, 240 a minute; sign-in attempts of any outcome, 20 a minute) and answers 429 with `Retry-After` inside the CORS layer, health endpoints exempt. The client address is the hop a trusted proxy appended to `X-Forwarded-For`, never the hop the caller sent. `app/services/quotas.py` counts open drafts per operator (20) and verification runs per applicant (60) and per platform (1,000) over a rolling day in the database; over quota, a draft is refused with a 409 that says how to free a slot, and a verification run is stored `unavailable` with reason `daily_limit_reached` so nothing reaches the model and the application can still be submitted. All limits are settings; 0 disables; the CI browser suite disables the windows.

## Rationale

- Cost is the only limit that has to be exact, and it is counted where the truth lives (`verification_runs` rows), not in memory.
- The windows are deliberately per process: the deployment is one process, and a distributed attack is the edge's job (recorded in `SCOPE.md` since Sprint 1 and in `SECURITY_REVIEW.md`).
- Refusing a model call is safe because the check never decides anything; refusing a draft is safe because a draft can be deleted; nothing else is refused.

## Consequences

- A second backend process would double every window; the production step is the same windows in Redis or a limit at the edge.
- Provider failures count toward the daily ceilings (a run is a run); acceptable, because they are rare and the ceiling is generous.
- The limits are static and silent; a production version would expose the counters to the admin and alert on approach.

## Validation

`tests/unit/test_rate_limit.py` (window arithmetic, bucket choice, forwarded-for hop, map bound), `tests/integration/test_abuse_limits.py` (sign-in flood, general limiter, draft cap, daily quota, headers), `docs/security/SECURITY_REVIEW.md` (the four attacks before and after).
