# Production readiness review

An honest gap list for PermitFlow as shipped in v0.3.0 (19 Sep 2026), by area, with severity for a real licensing authority (not for the assessment demo), what is in place today, and what production would need. Severity: **High** (would block a real go-live), **Medium** (fix in the first weeks), **Low** (improvement). Items marked "by design" are recorded decisions in `SCOPE.md` or an ADR.

## Summary

The shipped system is a complete, tested vertical slice of use cases 1 and 2 with server-side authorization on every route, an explicit state machine, immutable revisions, same-transaction audit, an advisory AI verifier behind an interface, a seven-job CI, two isolated environments and a human-approved production deploy. What separates it from a production licensing system is mostly infrastructure and operations (queue, object storage, identity, observability, retention) plus the deferred use case 3. Nothing in the list below is hidden by the code or the docs.

## Gaps

| # | Area | Gap | Severity | Today | Production would need |
|---|------|-----|----------|-------|-----------------------|
| 1 | Functional | Use case 3 (site-visit checklist and post-site clarification) | High for the full product, by design for this release | Two post-site statuses and transitions exist and are tested; not reachable from the UI | Checklist model and screens, per-item clarification, operator response with uploads (US-060 to US-066) |
| 2 | Identity | Seeded accounts, email and password only; no registration, reset, MFA or SSO | High | Argon2, JWT 8 h re-validated per request, login rate limit | OIDC (Singpass/Corppass for operators, agency SSO for officers), MFA for officers and admins |
| 3 | Session | JWT held in `sessionStorage` | Medium | Accepted for a demo; XSS is mitigated by React escaping and security headers, not by a CSP | httpOnly, SameSite cookie with CSRF token; short access token plus refresh |
| 4 | Frontend security | No Content-Security-Policy | Medium | Other security headers set on API and nginx | A strict CSP with nonces; report-only first |
| 5 | AI checks | Background tasks in the API process (ADR-004) | Medium | Restart marks running checks failed; re-run recovers; one entry point | Broker plus worker (Redis/RQ or Celery), retries, dead-letter, per-run cost accounting |
| 6 | Files | Local disk on a Railway volume behind `FileStorage` | Medium | Server keys, magic bytes, allowlist, 10 MB, authorised download only | S3-compatible object storage, signed URLs, virus scanning (ClamAV or vendor) with a quarantine state, lifecycle rules |
| 7 | Rate limiting | In-process limiter on login only | Medium | Proxy-aware (`TRUSTED_PROXIES`) | Edge rate limiting and WAF; per-user quotas on uploads and re-runs |
| 8 | Data protection | Extracted document text sent to OpenAI; no retention or redaction policy | High for a regulator, documented (SCOPE assumption 16, T18) | Capped text, no images, provider and prompt version audited per run | Regional endpoint or self-hosted model, DPA, redaction of personal data before the call, retention schedule |
| 9 | AI quality and assurance | 14-case golden set and a 21-run name-swap fairness check; confidence uncalibrated; English-only injection heuristic; no bias evaluation beyond name invariance; images unreadable | Medium | Six-stage AI gate on every push (`ai-gate.yml`: model approval, contracts, golden set, adversarial, fairness, verdict); live run against OpenAI as its own workflow (`ai-eval.yml`, nightly and on AI changes, 14 of 14 blocking, prompt version stamped); deterministic injection rule | Labelled set from officer overrides; promptfoo threshold gate and injection red-team suite driving the real pipeline; Project Moonshot (AI Verify Foundation) runs mapped to IMDA's Starter Kit for Testing LLM-Based Applications and the Model AI Governance Framework for Generative AI (testing and assurance, security, incident reporting); a multilingual injection classifier (Llama Prompt Guard 2) in place of the English-only heuristic; per-run traces with tokens and cost in self-hosted Langfuse or LangSmith (OpenTelemetry GenAI attributes); confidence calibration (reliability diagram, Brier score); a bias pass (Moonshot bias benchmark, accuracy per issue code by document language); OCR |
| 10 | Notifications | In-app only; email mocked | Medium | Notification rows in the same transaction, bell with unread count | Email/SMS adapter with delivery status and retries |
| 11 | Audit | Append-only table in the same database | Medium | No update or delete path in code; readable by officers; same transaction as the change | Tamper-evident store (hash chain or WORM), export, admin access audited per view |
| 12 | Concurrency | Single replica, one region | Low | Row locks and `version` protect correctness | Two replicas behind Railway's balancer once the AI checks move to a worker |
| 13 | Delivery | Migrations run on container start; no staging copy of production data | Medium | Health gate fails the deploy; rollback by `sha-` tag | Migration rehearsal against a staging clone, blue/green or canary |
| 14 | Backups | Railway's managed Postgres backups only; no file backup or restore drill | High | Separate volumes per environment | Scheduled backups for database and files, tested restore, retention policy |
| 15 | Observability | Structured logs with request ids; Railway metrics | Medium | 503 on pool timeout, error envelope with request id | Centralised logs, tracing, alerting on health and error rate, dashboards (admin epic US-070 to US-072 not built) |
| 16 | Supply chain | pip-audit and npm audit non-blocking; no SAST | Low | gitleaks blocking; pinned dependencies (`uv.lock`, `package-lock.json`) | Blocking audits once the baseline is clean, Semgrep (PR-blocking) and CodeQL on `main`, Trivy on the GHCR images with an SBOM |
| 17 | Certificate | Base-14 fonts (Latin only); no digital signature; no public verification page | Low | Hash recorded, verification code printed, owner-or-officer download (T20) | CJK-capable font, PAdES signature, verify-by-code endpoint |
| 18 | Product | One licence type, fixed form schema; no officer assignment | Low, by design | Form schema shared between server and client | Configurable schemas, assignment and workload routing |
| 19 | Accessibility | Keyboard and screen-reader paths checked by hand on the main screens; no automated a11y suite | Low | Semantic markup, labels, focus management in dialogs, reduced-motion support | axe in Playwright, an audit against WCAG 2.2 AA |
| 20 | Load | No load or soak testing | Low | Pool sizing configured (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`) | k6 or Locust runs against staging before go-live |

## What is ready

- Authorization: role per router, ownership as 404, sub-resource checks, one test per endpoint per role (22 × 403, 15 × 404 assertions).
- Integrity: state machine as data (588 tested combinations), row locks with an optimistic version, immutable revisions, audit rows in the same transaction, licence issued in the approval transaction.
- Input handling: error envelope everywhere, Pydantic 422 with field details, upload allowlist and magic bytes, `Content-Length` pre-check, 10 MB.
- Tests: 730 backend (real PostgreSQL, migrations from scratch), 51 vitest, 7 Playwright specs in CI against the full stack.
- Delivery: images built once, GHCR tags with `sha-`, two environments that share nothing, production behind a required reviewer, health gates after the rollout, rollback by tag.
- Docs: every document in `docs/README.md` describes what exists; reviews record every finding and its outcome.

## Go / no-go for the assessment demo

Go. The development environment is live and seeded; production goes live with v0.3.0 on the owner's domain behind the approval gate. For a real authority: no-go until items 1, 2, 8 and 14 are addressed.
