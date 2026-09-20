# 06 Security

The threat model was written before the code (17 Sep 2026) and amended in place, with dates, as controls were built or changed; the security review was written on the last day of the sprint against the code as it was. Together they answer "what could go wrong" and "what did you do about it".

| Document | What it holds |
|----------|---------------|
| `THREAT_MODEL.md` | Assets, trust boundaries, threats T1 to T23 (plus T1a): the risk, the control planned for the MVP, how it was validated, and the production gap where one remains |
| `SECURITY_REVIEW.md` | The owner's twelve-item hardening checklist and four abuse scenarios (US-058), item by item: what the code did before, what it does now, the test, and what production would add |

The controls themselves live in the code: authorization and ownership in the services and repositories (ADR-005), the rate limiter and quotas (ADR-012), upload validation, the security headers. Every endpoint has an authorization test; `../08-testing/TEST_STRATEGY.md` says where.

Related: the legal and privacy side of the same questions is `../11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md`; the AI-specific threats (prompt injection, third-party data transfer) are in the threat model and detailed in `../07-ai/`.
