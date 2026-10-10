# ADR-018: The session travels in an HttpOnly cookie, behind a switch

Date: 10 October 2026. Story: US-104 (wave 3a of v0.5.0, backend only; the frontend follows in wave 3b). Status: accepted, built behind a switch (`AUTH_MODE`) whose default is the old behaviour; not switched on in any deployed environment. Related: ADR-005 (server-side authorisation), US-093 (one session per account), US-101 (the settings panel, a dependency of the plan), threat model T12, T14, T27.

## Context

Since the first sprint the signed-in session is a JWT that the frontend keeps in `sessionStorage` and sends in an `Authorization: Bearer` header. T14 has always named the weakness: a script injected into the page (XSS) can read the token and use it from anywhere for up to eight hours. The other controls (React escaping, a strict CSP, no `dangerouslySetInnerHTML`) make XSS unlikely, not impossible, and a stolen token is the worst thing an XSS can take.

US-093 already made the token a handle on a server-side session row (`sid`), checked on every request, so a session can be ended from the server. That is the property that makes a cookie safe to adopt: the cookie holds the same token, and revocation, take-over and the idle limit keep working unchanged.

The deployment shape matters for the design. The frontend is at `https://dev.permitflow.space` and the API at `https://api.dev.permitflow.space`: the same site (registrable domain `permitflow.space`), different origins. So `SameSite=Strict` cookies set by the API are sent on the frontend's `fetch` calls (same site), but a script on the frontend cannot read them (a host-only cookie on the API host is invisible to `document.cookie` on the frontend host).

## Constraints

- Default behaviour unchanged: every existing test passes untouched with `AUTH_MODE=token`.
- Reversible with a setting (build control, 9 Oct 2026): rolling back is setting `AUTH_MODE=token` and redeploying the API, because the settings are read once at startup. No migration, no data change.
- No credential the frontend can read in cookie mode, and no wildcard CORS.
- One live session per account, take-over and revocation keep working (US-093).
- No schema change, no new dependency.

## Options considered

### Option A: keep the bearer token, harden the page further
A stricter CSP and a trusted-types policy reduce XSS further but leave the token readable by whatever script does run. Does not meet the story.

### Option B: a cookie that holds the token, with a CSRF token (chosen)
The session cookie is `HttpOnly`, so no script can read it. The browser attaches it automatically, which re-opens CSRF; a double-submit token closes that.

### Option C: a cookie plus server-side opaque session ids instead of the JWT
Cleaner in theory (nothing to decode), but the JWT already carries `sub`, `sid` and the expiry, and the session row is already checked per request. Replacing it is a larger change for no extra safety here.

### Option D: a refresh token in a cookie and a short access token in memory
The usual SPA answer, but it needs a refresh endpoint, rotation and a second token lifetime. The session row already gives revocation, so the extra moving parts buy nothing at this size.

## Decision

Option B, behind `AUTH_MODE=token|cookie` (default `token`).

**One transport per mode.** In `token` mode the dependency reads the `Authorization` header only and ignores cookies. In `cookie` mode it reads the session cookie only and ignores the header. Accepting both in cookie mode would leave a header path that skips the CSRF check and the HttpOnly protection, and would let a leaked old token keep working; the cost of refusing is nothing, because the frontend of wave 3b stops sending the header.

**Cookies (cookie mode, set at sign-in).**

| Cookie | Value | Attributes |
|--------|-------|------------|
| `__Host-pf_session` | the JWT (carries `sub`, `sid`, `exp`) | `Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=<JWT_EXPIRES_MINUTES * 60>`, no `Domain` |
| `__Host-pf_csrf` | the session-bound CSRF value below, as hex | `Secure; SameSite=Strict; Path=/; Max-Age=<same>`, not HttpOnly, no `Domain` |

The `__Host-` prefix makes the browser refuse the cookie unless it is Secure, Path=/ and has no Domain, so a sibling subdomain cannot plant or overwrite it. Sign-out sends both again with `Max-Age=0` and the same attributes.

**The sign-in body carries no bearer token.** It is `{ expires_at, user, csrf_token }`. `GET /auth/me` (the existing endpoint) also returns `csrf_token` in cookie mode, so a page reload learns who is signed in and gets the value again without reading any cookie. In token mode both bodies are exactly as before (`/auth/me` omits the field).

**CSRF: double submit, bound to the session.** Every unsafe method (anything but GET, HEAD, OPTIONS) on an authenticated route must send `X-CSRF-Token`. The server accepts it only if the header equals the CSRF cookie and equals the value derived from the request's own session id, each compared with `hmac.compare_digest`. The value is `HMAC-SHA256(k, session id)` where `k = HMAC-SHA256(JWT_SECRET, "permitflow-csrf-v1")`, a sub-key, so the key that signs the tokens never signs the CSRF values directly. Binding to the session means a value planted for, or minted by, another session fails; knowing the algorithm without `JWT_SECRET` is not enough. Every refusal writes one structured `csrf_failed` log event (reason, method, path, user id; never a token value). The failure is `403 csrf_failed`. The check sits in `get_current_user`, after the session check, so every authenticated unsafe route is covered by the one place the route-lock test already proves every route uses, and a revoked session still answers `401 session_revoked`.

**Why the token also travels in the body.** The frontend and the API are different hosts, so the frontend's script cannot read the API-host CSRF cookie that classic double submit expects. The server therefore hands the same value over in the body and the frontend keeps it in memory. This is safe: the CSRF value is not a credential (it is useless without the HttpOnly cookie), and the check still requires the cookie to be present and equal. The cookie remains readable (not HttpOnly) for same-origin setups such as local development.

**Sign-in itself.** There is no session yet, so no token to compare. It is protected by two things: `SameSite=Strict` on the cookies it sets, and an `Origin` check before the password is looked at. In cookie mode the request must carry an `Origin` header equal to one of `CORS_ORIGINS`; otherwise `403 csrf_failed`, with no cookie and no hint about the password or the live session. Every browser sends `Origin` on a cross-origin POST, so the frontend needs no change; command-line clients must send it. This prevents login CSRF (an attacker page signing the victim into the attacker's account). The existing limiters (T13) still apply.

**CORS.** In both modes, whenever `CORS_ORIGINS` is an explicit list: `Access-Control-Allow-Credentials: true` and `Access-Control-Allow-Origin` echoing only an origin in `CORS_ORIGINS`. Token mode needs it because the frontend sends credentials on sign-in and on its load-time `GET /auth/me` before it knows the mode, and a browser refuses the answer to a credentialed request without `Allow-Credentials`; token mode ignores cookies, so it opens nothing there. A token-mode `CORS_ORIGINS=*` still starts (non-browser clients) but never gets credentials, so the browser frontend cannot sign in against it: list the frontend origins. `X-CSRF-Token` is added to the allowed headers in cookie mode only (token mode never needs it). Startup refuses `AUTH_MODE=cookie` when `CORS_ORIGINS` is empty or contains `*`, when any entry is not a bare `scheme://host[:port]` (a path, a trailing slash and the literal `null` are refused: an Origin header never carries a path, and `null` is what sandboxed pages send), and in production when any entry is not `https://` (the cookie is Secure). Otherwise token-mode CORS is as before.

**One session per account.** Unchanged and tested in cookie mode: a second sign-in is `409 session_active` (and sets no cookie); `take_over: true` revokes the other session, whose cookie then answers `401 session_revoked`.

## Consequences

- An injected script can still make requests as the user while the page is open (it runs in the page); it can no longer copy the session away. T14 moves from "token stolen" to "session used only while the page is open".
- The frontend (wave 3b) must send `credentials: "include"`, stop storing a token, keep `csrf_token` in memory, send `X-CSRF-Token` on writes, and call `GET /auth/me` on load. The two XMLHttpRequest upload paths (`frontend/src/api/documents.ts` and `frontend/src/api/clarification.ts`) do not go through `fetch`: each needs `xhr.withCredentials = true` and the `X-CSRF-Token` header, and drops its `Authorization` header, or every upload answers 401 or 403.
- A stale cookie cannot be cleared from script. If the session ended elsewhere, the cookie stays until `Max-Age` or the next sign-in; every call it makes is a `401`, which the frontend treats as signed out. Sign-out is the exception that cleans up: `POST /auth/logout` clears both cookies even when it is refused as `401` (revoked, expired or missing session).
- Downloads and images served from the API now work with the cookie alone (no bearer needed in a URL).
- Local development: `__Host-` needs Secure. Chrome and Firefox accept Secure cookies on `http://localhost`; Safari does not, so use Chrome or Firefox, or stay in token mode locally.
- The automated suites that sign in over the API (UAT scripts, Playwright) keep `AUTH_MODE=token` until wave 3b moves the frontend; a cookie-mode run must send `Origin`.

## Frontend (wave 3b)

One client serves both modes, with no build flag or variable. The sign-in answer decides: `access_token` present is token mode (unchanged: `sessionStorage`, bearer header); absent with `csrf_token` is cookie mode (`credentials: "include"` on every request, the CSRF value in memory only and sent as `X-CSRF-Token` on POST, PUT, PATCH and DELETE, nothing in `sessionStorage` or `localStorage`, `withCredentials` plus the header on the two XMLHttpRequest uploads). The sign-in and the load-time `GET /auth/me` always send `credentials: "include"` (both server modes allow credentials for the listed origins, see CORS above); there is no probe, retry or fallback. In token mode this means one extra `GET /auth/me` (a 401) on a load with no stored token. A reload with no stored token asks `/auth/me`: a cookie session restores the user and its CSRF value. `403 csrf_failed` re-reads `/auth/me` and retries the request once. Flipping `AUTH_MODE` needs no frontend rebuild.

## Rollout and rollback

The switch is the rollback. Set `AUTH_MODE=cookie` on the API and deploy the frontend of wave 3b together; to go back, set `AUTH_MODE=token` (or unset it) and redeploy the API (the setting is read at startup, so a redeploy or restart is what applies it). Either change signs everyone out once (the frontend of the other mode does not hold the credential the API now wants). No data changes, no migration. See `OPERATIONS.md`.

## Revisit when

An XSS can be shown to do damage within the open-page window that the cookie does not stop (then: short access tokens and a step-up on sensitive writes); the frontend and API move to different registrable domains (SameSite=Strict then blocks the cookie: use `Lax` with the CSRF token, or one host behind a proxy); or an identity provider replaces our sign-in (the cookie then carries its session instead).

## Validated by

`backend/tests/integration/test_cookie_session.py` (exact attributes, no token in the body, header-only and cookie-only transports, Origin check, CSRF missing, wrong, planted and from another session, safe methods, sign-out clears and ends the session, one session per account with take-over, credentialed CORS for the listed origins only, token mode unchanged) and `backend/tests/unit/test_settings.py` (startup rules).
