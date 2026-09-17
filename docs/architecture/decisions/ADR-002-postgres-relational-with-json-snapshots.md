# ADR-002: PostgreSQL relational model with JSON revision snapshots

## Context
The domain has users, applications, revisions, documents, verification runs, feedback, notifications and audit events, with strict integrity requirements ("no applications are lost", "data is never lost between rounds", "complete audit trail"). Form data is a fixed but nested structure (sections → fields).

## Constraints
- Managed Postgres is available on the deployment platform.
- Tests must be runnable in CI and locally; Docker is available locally.
- Three days: schema must be simple enough to migrate once or twice, not daily.

## Options Considered

### Option A: PostgreSQL, normalised tables, form data as a JSON column on each revision
- Pros: relational integrity for everything that has relationships; JSON for the one thing that is naturally a document (a form snapshot); Alembic migrations; SQLAlchemy 2 typed models.
- Cons: field-level querying of form data is awkward (not needed).

### Option B: Fully normalised form data (a row per field value per revision)
- Pros: queryable per field.
- Cons: many rows, complex diff queries, schema churn whenever the form changes. No requirement needs it.

### Option C: Document database (MongoDB)
- Pros: natural fit for snapshots.
- Cons: weaker transactional guarantees across collections for "revision + status + audit + notification" in one commit; not offered by the deployment platform's managed tier; less familiar to reviewers.

## Decision
Option A, PostgreSQL only. No SQLite fallback: the row locking (`SELECT … FOR UPDATE`), native UUID and JSONB features we rely on do not exist there, and a second engine is a second thing to keep green in three days.

## Rationale
Everything with relationships and invariants is relational; the one document-shaped thing is stored as a document. This is the smallest schema that satisfies every auditability requirement.

## Consequences

### Positive
- Foreign keys and unique constraints (for example `unique(application_id, revision_number)`) enforce integrity at the database.
- Revision snapshots are immutable rows; comparing revisions is a pure function over two JSON values.

### Negative / Tradeoffs
- Reports that query inside form data would need JSON operators or a later normalisation.
- Tests require a running Postgres (Docker locally, service container in CI).

## Validation
- Alembic migration applies cleanly on a fresh Postgres in CI.
- Integration tests run on Postgres in CI (service container) and locally against the Docker Compose database (`TEST_DATABASE_URL`).
