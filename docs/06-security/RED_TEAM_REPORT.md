# Red-Team Report (US-107)

Date: 2026-10-12
Target: PermitFlow v0.5.0-rc.5 (commit 981fe57), local stack only.
Branch: `test/us-107-red-team`.

## Scope and setup

A local stack started by the exercise: Postgres in Docker on 5460 (`pf-us107-db`), backend on 8030, no
frontend. No external host was touched (never dev/prod/Railway). No live AI (`AI_PROVIDER=mock`, no OpenAI/
LangSmith/Telegram keys). Exercised in both `AUTH_MODE=token` and `AUTH_MODE=cookie`
(`CORS_ORIGINS=http://localhost:3030`), `SCAN_MODE=off` (no clamd available locally; see coverage),
`VERIFICATION_MODE=inline`. Scripted HTTP only (urllib/http.client/curl); no ZAP (no local binary/image);
Chrome tools not used. Seed accounts from `scripts/seed.py` (local demo values); a second operator
(`operatorb@…`) was created for cross-tenant tests.

Overall: the application is strongly hardened. Authorization (role + ownership-as-404 + sub-resource
chain checks), the state machine, admin step-up and bounds, cookie/CSRF handling and upload validation all
held under empirical probing. One confirmed weakness was found in the rate-limiting trust chain.

## Findings

| id | persona | class | severity | one line |
|----|---------|-------|----------|----------|
| R-1 | Outsider / corrupt officer | Broken rate limiting (SEC-010 / T4) | medium | uvicorn's default proxy-header handling rewrites `request.client` from a forged `X-Forwarded-For`, so the per-client login/request limiters can be bypassed one bucket per spoofed IP |
| R-2 | Outsider | Information disclosure | low (fixed) | `/api/openapi.json` and `/api/docs` serve the full API schema unauthenticated in non-production, incl. the internet-facing `dev` environment |
| R-3 | Outsider | Information disclosure | info | `/api/v1/health` returns version, commit and environment unauthenticated |
| R-4 | Malicious operator | Resource exhaustion | low (fixed) | re-running verification once over the AI quota still writes a `verification_run` + audit row per request; unbounded except by the (bypassable, see R-1) request limiter |

### R-1 (medium) — X-Forwarded-For rate-limit bypass via uvicorn proxy headers

Place: `backend/app/core/rate_limit.py:client_key` (reads `request.client.host`) + `backend/Dockerfile:14`
(uvicorn launched with no `--forwarded-allow-ips`).

`client_key` is written carefully: with no trusted proxy it returns the socket address and ignores
`X-Forwarded-For`, "so a caller cannot pick a fresh bucket per request (T4)". That assumes `request.client`
is the true socket. uvicorn's `ProxyHeadersMiddleware` runs ahead of the app with its default
`forwarded_allow_ips="127.0.0.1"` and **overwrites `scope["client"]` from the caller-supplied
`X-Forwarded-For`** whenever the immediate peer is trusted. `client_key` then keys on the spoofed value.

Reproduced on the local stack (cookie mode, login limiter = 10/min):
- 25 failed logins each with a distinct `X-Forwarded-For: 10.0.0.<i>` (new connection each) → all `401`,
  never `429`. uvicorn's access log recorded the peers as `10.0.0.18:0 …` (the forged values).
- 300 failed logins over one persistent connection → blocked at the 11th (`429`).

Impact: defeats login brute-force protection and per-client request throttling (SEC-010, US-058) for the
default/local/self-hosted and CI-E2E configurations. Production on Railway is *probably* mitigated because
the edge sets `X-Real-IP` and the app prefers `CLIENT_IP_HEADER` with `TRUSTED_PROXIES=*` — but the app
still keys on `request.client.host`, which uvicorn fills from the *appendable* `X-Forwarded-For`, so the
mitigation is implicit and unverified (whether the edge strips inbound `X-Forwarded-For` was not tested).
Rated medium on that basis; it is high for any non-Railway/self-hosted/local deployment.

Fix: launch uvicorn so a forged `X-Forwarded-For` cannot rewrite `request.client` for an untrusted peer —
`--forwarded-allow-ips=` (trust nobody) and let `client_key` resolve the client, or pin it to the single
edge address. Then `client_key` is the one source of truth, as designed.

Reproducing test: `backend/tests/redteam/test_r1_forwarded_for_ratelimit_bypass.py`
(`test_forged_x_forwarded_for_cannot_bypass_the_login_limiter`, `xfail(strict, reason="US-107 R-1")`).

### R-2 (low) — unauthenticated API schema in non-production

Place: `backend/app/main.py:create_app` (`expose_docs = settings.app_env != "production"`).

`/api/openapi.json` and `/api/docs` return `200` with the full route/schema inventory when
`APP_ENV != production`. This is intentional (THREAT_MODEL: no public schema in production only), but the
`dev` environment (`https://dev.permitflow.space`) is internet-facing and runs as `development`, so the
whole API surface is public there. Consider gating docs behind auth or an allowlist even in non-prod, or
documenting the accepted exposure. No reproducing test (accepted-by-design; low).

**Fixed** (`fix: close red-team low findings R-2 and R-4`, branch `fix/red-team-lows`): the new setting
`EXPOSE_API_DOCS` (default false) gates both URLs, and production never serves them even when it is set. The
route-coverage smoke script reads the routes in process; the CI end-to-end job and `.env.example` set the flag.
Tests: `test_api_docs_are_off_by_default_and_never_in_production`.

### R-3 (info) — health detail unauthenticated

Place: `backend/app/api/v1/health.py`. `version`, `commit` and `environment` are returned without auth,
aiding fingerprinting. Intentional (deploy-gate/monitor need it) and low value to an attacker; noted only.

### R-4 (low) — verification re-run row growth not quota-bounded

Place: `backend/app/services/verification.py:rerun` + `services/quotas.py`. Once an applicant is over the
AI daily quota, re-runs are stored as `unavailable` with no model call (good, no cost), but each request
still inserts a `verification_run` and a `verification.requested` audit row. The only ceiling is the
per-client request limiter, which R-1 can bypass. Low: no AI spend, bounded storage per request, owner-only
on their own editable document. Fixing R-1 removes the practical lever. No separate reproducing test.

**Fixed** (`fix: close red-team low findings R-2 and R-4`, branch `fix/red-team-lows`): `VerificationService.rerun`
asks `verification_over_quota` (the rule the upload path uses) before it writes anything and answers 429
`rate_limited` with `details.code = daily_limit_reached`; no run and no audit row is inserted. The upload path
keeps storing its refused run, because the file itself is stored. Test:
`test_a_rerun_over_the_quota_is_refused_without_writing_a_run_or_an_audit_row`.

## Coverage table

| Persona | Area | Status | Notes |
|---------|------|--------|-------|
| 1 Malicious operator | IDOR: read/submit/patch/delete another operator's application | tested — safe | `ApplicationRepository.get_for` → 404 cross-tenant (empirical) |
| 1 | IDOR: document download across tenants | tested — safe | 404 for other operator and for officer on a draft |
| 1 | IDOR: licence / compare / clarification-attachment across tenants | tested (code) — safe | all route through `get_for`; attachment walks attachment→…→application and 404s a foreign id |
| 1 | Approval / certificate without licence or site visit | tested — safe | no edge to APPROVED except via PENDING_APPROVAL; licence download 404 before approval |
| 2 Corrupt officer | Admin-only routes, admin mutating a case | tested — safe | admin `transition` → 403; admin is read-only by construction (no `Actor`) |
| 2 | Skip state-machine steps / forbidden edges | tested — safe | `domain/workflow.py` edge table + actor + guard; operator→officer edge 403 |
| 2 | Replay / race two officers on one case | tested (code) — safe | row `FOR UPDATE` + `expected_version` optimistic check; not driven to a live 2-officer race (time) |
| 2 | Officer approving own conflict of interest | not applicable | no officer-assignment/segregation model exists (documented product decision) |
| 3 Stolen admin | Raise a limit past its hard bound | tested — safe | `upload_max_bytes` 99 MB → 422; bounds re-checked at read time too |
| 3 | Flip scanner fail mode "open" | tested — safe | choices are only `retry`/`hold`; `open` → 422; no choice opens an unscanned file |
| 3 | Settings/user change without step-up | tested — safe | missing password → 422; wrong password → 403 `step_up_failed`, counts to login limiter |
| 3 | Pause AI / revert abuse / audit gaps | tested (code) — safe | pause is audited + step-up; revert re-validates bounds; every change audited |
| 4 Outsider | Metrics unauthenticated | tested — safe | `/metrics` → 404 when `METRICS_TOKEN` unset; bearer required when set |
| 4 | openapi/docs, health detail | tested — findings R-2 / R-3 | |
| 4 | Login enumeration / generic errors | tested — safe | identical message + dummy-hash verify for unknown vs wrong password |
| 4 | Login timing oracle | tested (light) — no signal | ~60-70 ms per attempt either way (single argon2); not statistically profiled |
| 4 | Rate-limit bypass with forged X-Forwarded-For | tested — finding R-1 | |
| 4 | Security headers / CORS / `--no-server-header` | tested — safe | CSP `default-src 'none'`, nosniff, XFO DENY, HSTS, strict CORS, no wildcard |
| 5 Malicious uploader | Content-type lie / polyglot (html-as-pdf) | tested — safe | magic-byte check → 400 `content_mismatch` |
| 5 | Disallowed / double extension (svg, x.pdf.exe) | tested — safe | extension allowlist → 400 |
| 5 | Path traversal in filename | tested — safe | `../../etc/passwd.pdf` stored as `passwd.pdf`; server-generated storage key |
| 5 | Stored XSS via filename / clarification text | tested — safe | `<script>` stripped from names; free text React-escaped; no `dangerouslySetInnerHTML` / raw sinks |
| 5 | XSS via download response | tested — safe | `.txt`+`<script>` served `attachment` + `text/plain` + nosniff + CSP `default-src 'none'` |
| 5 | Oversized upload | tested — safe | 11 MB → body-limit refuses from `Content-Length` before reading |
| 5 | Session/CSRF (cookie mode) | tested — safe | Origin check on login; double-submit CSRF (missing/wrong → 403); `__Host-` HttpOnly+Secure+SameSite=Strict; bearer ignored; logout revokes server-side, replay → 401 |
| 5 | ClamAV scan path / zip & image bombs / PDF JavaScript | NOT TESTED | needs `SCAN_MODE=enforce` + clamd; no clamd locally and none already running. PDF active-content detection (`domain/scan.pdf_active_content`) and quarantine flow unexercised |
| all | Worker/queue mode abuse | NOT TESTED | ran `VERIFICATION_MODE=inline` only; worker lease/reaper race not exercised |
| all | Side channels in logs/metrics/Telegram | tested (code) — safe | audit stores field names not values; infected alert carries only reference + signature; LangSmith uses keyed pseudonyms |
| all | ZAP active scan | NOT RUN | no local ZAP binary or image; nothing installed per rules |

## What was NOT covered (and why)

- ClamAV/virus-scan behaviour, zip/image bombs, PDF-JavaScript blocking: require `SCAN_MODE=enforce` and a
  clamd; none available locally and none already running, and the rules forbid installing anything.
- Worker/queue mode (`VERIFICATION_MODE=worker`): only inline mode was run.
- Two-officer concurrent transition race driven live: guarded in code (row lock + optimistic version); not
  reproduced end-to-end within the time-box.
- ZAP active scan: no local binary/image.
- Login timing analysed only lightly (no statistical profiling).
