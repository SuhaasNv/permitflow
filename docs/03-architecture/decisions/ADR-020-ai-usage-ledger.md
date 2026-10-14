# ADR-020: A ledger of what each check cost, written with the result

Date: 10 October 2026. Story: US-100 (wave 3 of v0.5.0). Status: accepted, built; behind no switch of its own (the Telegram line has the US-101 setting `telegram_per_check_messages`, off by default). Related: ADR-004 and ADR-016 (where checks run), ADR-006 (AI advisory), ADR-008 (same-transaction records), ADR-012 (quotas), ADR-014 (the administrator reads), US-101 (live settings).

## Context

The quotas (US-058) cap how many checks run, but nothing says what they cost or who started them. The OpenAI token counters on the dashboard (US-077) are process counters: they reset on a restart, carry no person and no application, and price every token at one constant written into the dashboard script. The licensing office asked for "a record of what each automatic check cost and who ran it, so that AI spend is visible per person and per application".

Three forces shape the answer:

1. **The record must be true.** A row that can disagree with the check it describes (written before the result, or after, or twice) is worse than none. Audit rows already solve this by sharing the result's transaction (ADR-008).
2. **Prices change.** A cost recomputed from today's price rewrites history. The price a check was charged must be the price in force when it ran.
3. **It leaves the building by four routes** (the administrator's page, Prometheus, Telegram, LangSmith), and three of them are third parties. What each may carry has to be decided once, here, not per call site.

## Options considered

### Option A: derive cost from the Prometheus token counters
Already there. But it has no person or application (adding either as a label breaks the bounded-label rule), loses history on restart, and cannot be exported.

### Option B: extend `verification_runs` with tokens and cost
One table, no join. But it mixes the queue (ADR-016: claimed, leased, requeued) with the ledger, a run deleted with its draft would take its cost with it, and a price needs its own versioned table anyway.

### Option C: a separate `ai_usage` table, plus `ai_prices` (chosen)
One row per run, written by the same code and in the same transaction that stores the result. Prices in a table of their own with an effective date. The ledger survives the deletion of a draft.

### Option D: an event stream or an external billing tool
More machinery than a few thousand rows a month need, and a second source of truth next to the database.

## Decision

Option C.

**Tables (migration 0017).**

- `ai_prices(id, model, input_per_million, output_per_million, effective_from)`, unique on `(model, effective_from)`. A price is never edited: a new row with a later date replaces it. The price of a run is the row of its model with the latest `effective_from` not after the moment the run started (when it was created, for a run that never started), so a price change while a check is in flight does not reprice it. The migration seeds the default model (`gpt-4.1-mini`, USD 0.40 and 1.60 per million tokens, effective 14 Apr 2025). There is no screen or endpoint to add a price: an operator inserts a row (documented in `OPERATIONS.md`).
- `ai_usage(id, run_id unique, document_id, application_id, user_id, document_type, provider, model, input_tokens, output_tokens, cost_usd, price_id, latency_ms, outcome, created_at)`. `cost_usd` is `NUMERIC(14,8)`. `run_id`, `document_id` and `application_id` are plain columns, not foreign keys: draft deletion removes the runs and documents, and the money already spent stays. `user_id` is a foreign key to `users` (accounts are deactivated, never deleted).
- `verification_runs.requested_by` (nullable foreign key to `users`): the person whose upload or re-run created the run. An officer's re-run is charged to the officer; the quota still counts against the application's owner, as before.

**One row per run, in the result's transaction.** `_finish` adds the row to the session that stores the result, the audit event and the status, and commits them together, in `inline` and `worker` mode alike (both call the same function). A result dropped because the draft was deleted or the lease changed hands writes no row. A failed commit rolls the row back with the result.

**Runs that never reached the provider still have a row**, with zero tokens and zero cost and their own outcome: refused by a quota or the AI pause switch at creation (`unavailable`), unreadable file, provider not configured, provider unavailable before billing. Runs ended by the system without a result get a row from the code that ends them: `dead` (the reaper) and `failed: interrupted` (the startup sweep and the stranded-run sweep), with zero tokens because none are known. A sweep skips a run that already has a row, so it can never trip the unique key and stop the reaper.

**Tokens come from the provider.** `VerificationProvider` gains `input_tokens` and `output_tokens`, set by `verify` (OpenAI: the `usage` block, recorded before the answer is parsed, so a malformed answer that was billed is counted). The mock reports zero. A provider is built per check, so the fields belong to one check. The cached-token discount is not applied: the price table has one input price, so `cost_usd` is an upper estimate of the invoice, which stays the truth.

**One Telegram rule.** A line is sent only for a check that reached a provider (a result, a provider error, a timeout). A check that never did sends nothing, wherever it stopped: refused by a quota or the pause switch when it was created, paused between creation and execution, an unreadable file, no provider configured, a replaced document, or ended by the reaper. The counters still count it.

**A model with no price row costs 0**, is logged as `ai_price_missing`, and still gets its row with `price_id` empty. A missing price shows up as a warning and a gap in the page, never as a failed check.

**What leaves the building.**

| Route | Carries | Never carries |
|-------|---------|---------------|
| Administrator page and CSV | the person's name and id, the case reference and id, document type, provider, model, tokens, cost, latency, outcome | document text, filenames |
| Prometheus | counters `permitflow_ai_checks_total`, `..._ai_tokens_total`, `..._ai_cost_usd_total` labelled by `document_type`, `outcome` (and `kind`) | any id, name or free-form string: both labels pass through `bounded_label` against the enum values, anything else becomes `other` |
| Telegram (per check, off by default) | document type, outcome, cost, time, the case reference; only for a check that reached a provider | names, email, filename, document content, tokens, the person's id |
| LangSmith (trace metadata) | run id, document id, document type, `application_hash`, `user_pseudonym` | application id, user id, email |

The pseudonyms are the first 16 hex characters of HMAC-SHA256 over a label (`user` or `application`) and the id, keyed with a sub-key derived from the server secret (`k = HMAC-SHA256(JWT_SECRET, "permitflow-pseudonym-v1")`, so the secret itself never keys the pseudonyms directly; the same derivation pattern US-104 uses for its CSRF token): stable, so one person's traces group together, and not reversible by anyone without the key. Rotating the secret changes every pseudonym, which only splits traces at that date. The Telegram send happens after the commit, through the existing notifier, inside a guard: a failure is logged and the check is not affected.

**The export** is `GET /admin/ai-usage.csv`, a streamed response from a session of its own, one line at a time. Every cell that begins with `=`, `+`, `-`, `@`, tab or CR gets a single quote in front, so a spreadsheet shows a person's name that starts with `=` as text. The export is bounded: at most 100,000 rows (the file then ends with a line saying it was cut and which filters narrow it), every statement under a 60 second `statement_timeout` (`SET LOCAL` on the export's own session), and each export writes one audit event, `admin.ai_usage_exported`, with the filters, the row count and whether it was cut, and no names. The event is written when the stream ends, also if the reader goes away halfway.

**Reads.** `GET /admin/ai-usage` is keyset-paged like the audit feed, filters by person, application and a Singapore day range (both ends included), and returns the totals over everything the filters match and today's numbers beside the live `ai_runs_per_day` cap. The cap itself is counted by the quota over a rolling 24 hours; the page reports the Singapore day, as the overview does, and `today.runs` is the number of checks that count toward the cap (not the number of ledger rows today: quota refusals and pause stops are left out).

## Rationale

- Writing the row where the result is written makes "a row for every stored result, and only for those" a property of one transaction rather than a promise between two.
- A separate ledger keeps the queue's churn (claims, leases, requeues) out of the table finance reads, and lets a draft be deleted without erasing the spend.
- Prices as dated rows make a past row immutable in meaning: its `price_id` says which price it was charged at.
- Closed label vocabularies turn "never put a person in a metric" from a review comment into a function with a test.

## Consequences

- One more row per check (a few hundred bytes) and a one-row price lookup per result. Negligible at this volume. A run has one row even when it is queued again (a scan hold, then a retry): the later attempt updates the row with its outcome, provider, model and latency and adds its tokens and cost to what is there, and the counters count each attempt's own tokens once.
- With `VERIFICATION_MODE=worker` the Prometheus counters are incremented in the worker process, so the worker's `/metrics` must be scraped for the dashboard and `/cost` to see them (the local Prometheus does; the Railway job exists for development). The page and the CSV read the database and are right in both modes.
- **The ledger can undercount; it never overcounts.** Tokens the provider billed are missing from every row in these cases:
  1. A result dropped because the lease changed hands (a slow worker whose run was taken back): the first attempt's tokens are lost, the row holds the second holder's. `permitflow_ai_unrecorded_tokens_total{kind}` counts them.
  2. A result dropped because the draft was deleted after the provider answered: counted the same way. The run itself is still counted by the daily quota: its row is written (zero tokens, outcome `running`) and committed just before the provider is called, so deleting the draft mid-call cannot erase it.
  3. A run the reaper marks `dead` after hung attempts that were billed: the row has zero tokens; if a hung attempt ever finishes it is dropped and counted as in case 1, if it never does nothing records it.
  4. A run ended by the system without a result (`failed: interrupted`): zero tokens.
  5. A crash after the provider answered is not an undercount: the crash handler keeps the billed tokens on the `failed` row. A crash inside the provider call before it reports usage is.
  The OpenAI invoice remains the truth; the unrecorded counter is the size of the gap the process can see.
- Runs before migration 0017 have no row (no backfill: nothing recorded their tokens). The page starts at the day the migration ran.
- No price administration UI. A new price is an `INSERT`; until one exists for a new model its checks cost 0 in the ledger.
- `cost_usd` ignores the cached-input discount, so it can sit slightly above the invoice.

## Validation

`backend/tests/integration/test_ai_usage.py` (real Postgres): a row with user, application, tokens and cost for an inline check; the price in force at run time among three versions, a future price ignored; zero rows for the mock, the pause switch, a quota refusal and an unreadable file; an officer re-run charged to the officer; the worker path; a failed commit leaving exactly one row after the retry; a dropped result leaving none; `dead` and swept runs recorded once; the page's filters, day range, cursor and totals; today against the live cap; administrator only (401, 403 for operator and officer) on both routes; CSV streamed with formula cells quoted for each leading character; bounded counter labels, including a hostile value; the Telegram line on, off, failing and containing no personal data; the LangSmith metadata; migration 0017 downgrading and upgrading with the seed. `tests/unit/test_ai_usage_domain.py` and `test_ai_usage_provider.py`: the arithmetic, the labels, the pseudonyms, the CSV rule, the provider token fields.

## Revisit when

- Prices need changing often or by someone who cannot run SQL: add an admin form over `ai_prices` (and an audit event).
- A second provider or model is used at the same time: the ledger already keys on model; the cached-token discount may then matter, and a `cached_tokens` column and price would be added.
- A spend cap in USD (the plan's denial-of-wallet row) is wanted: the ledger is the source for it; the quota today counts checks, not money.
- Retention rules for personal data apply to `user_id`: the ledger would need a pseudonymising job.

## Links

Stories: US-100 (this), US-098 (where checks run), US-101 (the Telegram setting, the daily cap). Documents: `docs/03-architecture/DOMAIN_MODEL.md` (tables), `docs/03-architecture/ARCHITECTURE.md` (API table), `docs/13-observability/OBSERVABILITY.md` (counters, dashboard row, `/cost`), `docs/06-security/THREAT_MODEL.md` (T34), `docs/09-operations/OPERATIONS.md` (prices, the switch), `docs/07-ai/AI_VERIFICATION_DESIGN.md`.
