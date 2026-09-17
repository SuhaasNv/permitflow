# ADR-004: Asynchronous in-process AI verification with polled status

## Context
The assessment requires "real-time AI verification status visible per uploaded document". Verification involves text extraction and an LLM call (seconds). The upload request must not block on it, and a provider failure must not break uploads or submissions.

## Constraints
- No message broker in the MVP (local setup and deployment must stay simple).
- Verification must be re-runnable and its history auditable.
- The pipeline must work with a mock provider (tests, no API key).

## Options Considered

### Option A: Synchronous verification inside the upload request
- Pros: simplest code.
- Cons: uploads take seconds; provider timeout fails the upload; drag-and-drop of several files serialises on the LLM. Contradicts the "status visible" requirement, which implies a state that changes over time.

### Option B: FastAPI `BackgroundTasks` in-process, `verification_runs` table with status, client polls
- Pros: upload returns immediately with status `pending`; status transitions to `running` then a terminal state; no extra infrastructure; the run record is queue-ready.
- Cons: a process restart mid-run leaves a `running` row; no retries across restarts; verification shares the API process.

### Option C: Worker process with Redis/RQ or Celery
- Pros: isolation, retries, horizontal scaling.
- Cons: broker locally and in deployment; more configuration and failure modes; time.

## Decision
Option B, with two mitigations: on startup, any `running` run older than the timeout is marked `failed` with reason `interrupted`; a re-run endpoint exists. Client polls every 2 seconds only while at least one document is `pending`/`running`.

## Rationale
The user-facing requirement is satisfied fully by B. C's benefits are operational, not functional, and are documented as the production path. The `run_verification(document_id)` function is the only entry point, so moving it to a worker is a change in who calls it, not what it does.

## Consequences

### Positive
- Uploads are fast and never fail because of the provider.
- Each attempt is a row with provider, model, latency, outcome and raw-output validity, giving observability for free.

### Negative / Tradeoffs
- Not durable across restarts; acceptable for MVP, mitigated by stale-run cleanup and re-run.
- Polling costs a request every 2 s per open application page while verifying; bounded and short-lived.

## Validation
- Integration test: upload → `pending` → task runs with mock provider → `verified`; a provider that raises → `failed`, upload still 201, submission still allowed.
- Startup cleanup test: a seeded stale `running` row becomes `failed`.
- E2E: document card changes state without page reload.
