# ADR-016: Document checks in a separate worker, with the database as the queue

Date: 9 October 2026. Story: US-098 (wave 2 of v0.5.0). Status: accepted, built behind a switch (`VERIFICATION_MODE`) whose default is the old behaviour; not yet switched on in any deployed environment. Supersedes ADR-004 for `worker` mode; ADR-004 still describes `inline` mode, which stays. Related: ADR-006 (AI advisory), ADR-008 (audit in the same transaction), ADR-012 (abuse limits), ADR-015 (object storage; the worker needs it to read files on Railway), US-101 (the AI pause switch and the worker concurrency setting), US-099 (virus scanning, next).

## Context

Since ADR-004 an uploaded document is checked by a FastAPI background task inside the API process. That was the right size for the assessment and has four limits that the v0.5.0 plan names:

1. **A restart loses work.** Background tasks live in the process. The startup sweep marks every `pending` run and every long-`running` run as `failed: interrupted`, so a deploy during a busy hour fails the checks in flight and the applicants have to re-run them.
2. **A hostile or broken PDF runs in the API process.** pypdf has a page cap and a 10 s budget that is only tested between pages (security audit run 3, lead 1). One page that takes minutes, or a file that inflates to gigabytes, holds a thread and memory of the process that also serves requests.
3. **Checks and requests share one process and one connection pool.** A burst of slow model calls competes with the API for threads.
4. **A deleted draft's text can reach the provider.** The task reads the file, calls OpenAI, then writes. A draft deleted in between has already been purged, but the call has been made and the text has left the system (deferred audit unit).

The files must also be readable by whichever process runs the check. On Railway a volume belongs to one service, which is why US-097 (ADR-015) came first.

## Constraints

- No new infrastructure to run, pay for or explain: no Redis, no broker, no new service besides the worker itself. Postgres 16 is already the system of record (ADR-002).
- Reversible with a setting, not a redeploy (build control, 9 Oct 2026: every risky part sits behind a switch whose default is today's behaviour). In `inline` mode the behaviour and the existing tests must be the same as before.
- The API contract does not change: the same statuses are served, the front end polls as it does now, quotas are enforced when the check is requested.
- AI stays advisory (ADR-006). A failed, dead or held check never blocks a submission.
- At-least-once delivery must be safe: a check run twice must not write two results or corrupt one.
- Local development, CI and the test suite run on one machine with a real Postgres.

## Options considered

### Option A: keep background tasks, harden them
Fix the page deadline and the re-check inside the API process. Cheapest, and it closes lead 4, but a restart still loses work, a hostile file still shares the API's address space, and the pool contention remains.

### Option B: Redis with a task library (RQ, Celery, arq)
Mature, but it adds a second stateful service with its own backup, failure and security story, a new dependency and a second place where "what is in flight" lives next to the database that already records every run. The queue would also have to be kept consistent with `verification_runs` (the row says `pending`, Redis says nothing, or the other way round).

### Option C: a Postgres-backed queue library (procrastinate, pgqueuer)
Same idea as the chosen option, but as a new dependency with its own tables and migrations, its own job model beside `verification_runs`, and its own idea of leases and retries. We would still need the pause switch, the re-check and the quota rules around it, and the run row is already the unit the UI reads.

### Option D: `verification_runs` is the queue (chosen)
The table already has one row per check with a status that the API serves. Add three columns, claim with `FOR UPDATE SKIP LOCKED`, wake with `LISTEN/NOTIFY`, track progress with a lease. One source of truth, no new dependency, and the claim is one statement that can be tested with real concurrent connections.

## Decision

Option D, behind `VERIFICATION_MODE=inline|worker` (default `inline`).

**The switch.**

- `inline`: exactly ADR-004. The request adds a background task; `run_verification` claims the run (`pending` to `running`, atomic) and executes it. The startup sweep of interrupted runs stays.
- `worker`: the request stores the run as `pending` (this is "queued") after the quota check, as today, and its background task only sends `NOTIFY verification_runs`. `python -m app.worker` claims and executes. The startup sweep is skipped (the queue survives an API restart); the workers' reaper handles expiry.
- A run over quota or created while the AI is paused is still stored finished (`unavailable`) at enqueue time in both modes, so it is never queued.

**Statuses.** `pending` is "queued", `running` is "claimed and leased", the existing finished statuses (`verified`, `issues_found`, `needs_review`, `unreadable`, `failed`, `unavailable`) are "done" and "failed". One value is new: `dead`, set by the reaper after the third claim. `status` is a `VARCHAR(16)` without a CHECK constraint, so the new value needs no DDL. Clients never see `dead`: both view services serve it as `failed` through `VerificationStatus.served`, the front end needs no change, and the operator's reason collapses to the generic `unavailable` as any infrastructure reason does. The applicant can re-run a dead check (it is terminal). The officer queue counts it as needing attention.

**Schema (migration 0016).** `attempts INTEGER NOT NULL DEFAULT 0`, `lease_until TIMESTAMPTZ NULL`, `worker_id VARCHAR(64) NULL`, and two partial indexes: `ix_verification_runs_queued (created_at) WHERE status = 'pending'` for the claim and `ix_verification_runs_lease (lease_until) WHERE status = 'running'` for the reaper. Downgrade first turns every `dead` row into `failed: interrupted`, so older code never meets a status it does not know, then drops the indexes and columns.

**Claim.** One statement, committed at once:

```sql
UPDATE verification_runs
   SET status='running', started_at=:now, lease_until=:lease, worker_id=:w, attempts=attempts+1
 WHERE id = (SELECT id FROM verification_runs
              WHERE status='pending' ORDER BY created_at
              LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id
```

The LIMIT is inside the subquery, so two workers cannot take the same row, and a worker never waits for a row another is claiming. The status literal is inlined (not bound) so the planner can use the partial index. After the commit nothing is held open: the run is protected by `lease_until` (`WORKER_LEASE_SECONDS`, 180 by default, above the 15 s PDF deadline plus the 30 s model timeout and its one retry). The worker's connections carry `lock_timeout` (`WORKER_LOCK_TIMEOUT_SECONDS`, 5 s), so a stuck row lock fails an attempt instead of hanging it.

**The worker loop.** It listens on the channel in its own thread (a dedicated autocommit connection, reconnecting after an error) and polls every 2 s, so a missed notification costs at most 2 s. Up to `worker_concurrency` checks run at once, one thread each. The value is the administrator's platform setting (US-101; the environment value `WORKER_CONCURRENCY`, default 2, is its ceiling), read live. On SIGTERM or SIGINT it stops claiming, gives running checks 8 s to finish (`docker stop` waits 10 s), and hands any run still unfinished back to the queue (`pending`, lease cleared, and `attempts` reduced by one because the interrupted attempt was not the run's fault).

**Reaper.** The worker runs it at start and every 60 s. A `running` run whose lease has expired goes back to `pending` (the claim already counted as an attempt), or to `dead` with `error_reason = worker_gave_up` once it has been claimed three times. A dead run gets the same `verification.completed` audit row as any finished check (status `dead`, attempts), in the same transaction. Several workers may reap at once; the updates are idempotent. A `running` run with no lease (inline mode) is never touched.

**Idempotent, fenced writes.** The result is written only by the holder of the run. `_finish` takes the row lock first (`SELECT ... FOR UPDATE` of the status and `worker_id`, with autoflush off) and proceeds only if the run is still `running` and still held by the executing worker; otherwise it drops the result and logs it. A check whose lease expired under a slow worker and was taken over therefore produces one result, from the worker that holds it. The provider may be called twice in that case; that costs money once, never correctness.

**Lifecycle re-checks.** After the text is extracted and before any provider is chosen, the check looks again: the run, its document and the application must still exist, and the document must still be the current revision.

- Gone (the draft was deleted; the purge deletes runs, then documents, then the application): the check returns, writes nothing, calls nothing.
- Replaced by a newer revision: the run is finished `unavailable` with reason `document_replaced`, with no provider call.
- Otherwise the transaction is committed (the extracted text is kept) and the connection is returned before the model call.

The second look is the write itself: the row lock above blocks the draft purge until the result is committed, and a run already deleted is simply not written. This applies in both modes (it is a privacy fix, not a worker feature); in `inline` mode it only changes the outcome of a race that used to send the deleted draft's text to the provider.

**Pause (US-101).** The worker does not claim while `ai_paused` is on. Runs queued before the pause stay `pending` (not failed, not unavailable) and run after unpause. A run already `running` when the switch flips is stopped at the existing check after extraction and stored `unavailable: ai_paused`, as in `inline` mode. New checks requested while paused are stored `unavailable` at enqueue time, as before.

**PDF extraction isolation (both modes).** `extract_text` runs pypdf in a child process: `python -I app/infra/pdf_text_child.py`, the PDF on stdin, JSON on stdout. The child sets `RLIMIT_CPU` and `RLIMIT_AS` before it imports pypdf; the parent kills it at `PDF_EXTRACT_TIMEOUT_SECONDS` (15 s). A timeout, a signal from a cap, a non-zero exit, unparsable output or a failure to start the child all return the reason a corrupt PDF returns today, `pdf_parse_error`, so the run becomes `unreadable` through the existing path and the applicant sees the same message. Stdlib only (`subprocess`, `resource`). `RLIMIT_AS` is not enforced on macOS; the wall-clock deadline and the CPU cap still are, and the container (Linux) enforces all three.

**Metrics.** `permitflow_verification_queue_depth`, `..._queue_oldest_seconds`, `..._active_leases`, `..._dead_runs` (gauges) and `..._reaped_total{outcome}` (counter), in `core/metrics.py`. The gauges are read from the database on every API scrape (so they are true in both modes) and every 10 s by the worker, which serves the whole registry on `WORKER_METRICS_PORT` (9100, private, no token, no published port). The counters and histograms of the checks themselves (`permitflow_verification_runs_total`, run seconds, OpenAI tokens) are updated by whichever process runs the check, so in `worker` mode Prometheus must scrape the worker too or those panels go flat; the local Prometheus config has the `permitflow-worker` job. The dashboard row comes from `build_dashboard.py`. The admin overview gains a `dead` count in its last-24-hours checks block.

## Rationale

- The run row is already the unit the API, the quotas, the audit trail and the UI read. A second queue would have to be kept in step with it; making the row the queue cannot disagree with itself.
- `SKIP LOCKED` plus a committed claim is the standard Postgres pattern for this size of work (a few runs a minute, each seconds long). Its failure modes (a worker that dies, a slow worker) are covered by the lease and the fence, and each is testable.
- Moving extraction to a child process fixes the hostile-file problem in both modes, with no new dependency, and keeps the failure path the applicant already knows.
- The switch makes the rollout a sequence of reversible steps: ship dormant, test in Compose, switch development, run the UAT, switch production at the release. Rollback is one variable.

## Consequences

- **A second process to run.** In `worker` mode a worker that is down means checks stay `pending` (the queue-age panel shows it; there is no alert rule yet). The checks are advisory, so submissions are not blocked.
- **Files.** On Railway the worker cannot read the API's volume. `worker` mode there requires `STORAGE_BACKEND=s3` (ADR-015) on both services; the worker logs a warning at start when it runs in production with local storage. In Compose both share the `uploads` volume.
- **Prometheus must scrape the worker** (the local config does; the Railway Prometheus, which scrapes the public API domains only, needs a private-network target when the worker service exists). Until then the check counters and the cost panels read zero in `worker` mode.
- **Switching back.** Setting `inline` and restarting the API: its startup sweep marks every `pending` and long-`running` run `failed: interrupted`, so queued checks are lost to the applicants, who re-run them. Drain the queue first (watch "Checks waiting") when that matters.
- **Pause while queued.** Runs queued before a pause show "Queued for checking" until it ends. The front end already treats a run older than the stale limit as no longer live.
- **Attempts.** `attempts` counts claims. A run that raised an exception inside the check is recorded `failed` by the existing handler and is not retried; only a worker that vanished or hung leaves a run to the reaper. A run is therefore retried only for infrastructure faults, which is the safe default for a paid, non-deterministic call.
- **The admin panel counts dead runs in the 24-hour window** like the other numbers; the gauge counts all of them.
- **`worker_concurrency` is reported `in_use: true`** by the settings API: the worker reads it live. (The API process never does; it is meaningful only with `VERIFICATION_MODE=worker`.)
- The worker adds a thread per check on top of the engine's pool (10 + 20 overflow); the ceiling of 32 for the setting is above what one pool serves, so keep the setting low (2 to 4) or raise `DB_POOL_SIZE` with it.
- No alert rule is added in this change (the plan names panels only). Candidates: oldest queued above 10 min, any dead run, worker target down.

## Validation

`tests/integration/test_verification_worker.py`, real Postgres, `VERIFICATION_MODE=worker` switched on per test:

- Thirty runs and six threads claim concurrently: every run claimed once, none twice, `attempts` 1, `worker_id` the claimant, oldest first, finished runs ignored.
- A worker that takes a run and dies: the reaper requeues it twice (lease still good is untouched), the third expiry makes it `dead` with `worker_gave_up` and an audit row; the applicant sees `failed` and may re-run; a dead run is never claimed; inline `running` runs without a lease are never reaped.
- A slow worker whose lease was taken over cannot overwrite the new holder's result; a lease that changes hands mid-run drops the old worker's write.
- A draft deleted during extraction, before the run starts, or after the provider call: the provider is called zero, zero and once times respectively and nothing is written back; a document replaced during extraction ends `unavailable: document_replaced` with no provider call.
- A crafted 5 KB PDF that inflates to 10 MB of operators is killed at the deadline (1.5 s in the test) and the run is `unreadable: pdf_parse_error`; the same file under a 1 s CPU cap; a normal PDF and an encrypted PDF are read correctly by the child; an unstartable child is the same failure.
- Pause: queued runs stay `pending` while paused and run after unpause. Concurrency: two slots, no more claims while both are busy. Shutdown: a stuck run goes back to the queue with `attempts` unchanged; a quick run finishes first. A database error does not stop the loop.
- A real `python -m app.worker` process runs a queued check and exits 0 on SIGTERM. NOTIFY reaches a listener and wakes the worker's listener thread.
- Migration 0016 downgrades (a `dead` row becomes `failed: interrupted`, columns gone) and upgrades back (indexes present). The queue gauges and the admin `dead` count.
- The rest of the suite, in the default `inline` mode and unchanged, is the evidence that inline behaviour did not change.

## Revisit when

- Throughput needs more than a few workers or a queue of more than a few thousand rows (index and `SKIP LOCKED` hold much further; the work per run is the limit, not the queue).
- A check needs to be retried after a provider error (a retry policy and backoff would be new; today an error is recorded).
- Runs need priorities (officer re-runs before bulk uploads), or per-applicant fairness beyond the quotas.
- US-099 adds the virus scanner: the worker is the natural place to call it, and the quarantine state would be a status.
- The Railway Prometheus can scrape the worker over private networking: add the job there and an alert on queue age and dead runs.

## Links

Stories: US-098 (this), US-097 (storage), US-099 (scanning), US-101 (pause switch, concurrency setting). Documents: `docs/03-architecture/ARCHITECTURE.md` (diagram, request flow, deployment), `docs/03-architecture/DOMAIN_MODEL.md` (the run's columns), `docs/06-security/THREAT_MODEL.md` (T32), `docs/13-observability/OBSERVABILITY.md`, `docs/09-operations/OPERATIONS.md` (running and stopping the worker, the switch, rollback), `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md` (rows 6 and 12), ADR-004, ADR-015, `SCOPE.md`.
