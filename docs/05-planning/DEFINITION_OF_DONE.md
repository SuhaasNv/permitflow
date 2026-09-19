# PermitFlow: Definition of Done

A story is Done only when every applicable item below is true. "Works on my machine" is the start, not the end.

## Functional
- [ ] Every acceptance criterion in `USER_STORIES.md` is demonstrably satisfied.
- [ ] The critical journey (submit → review → feedback → resubmit → compare) still works.

## Correctness and safety
- [ ] Input validated on the server (Pydantic) and, for forms, on the client (Zod).
- [ ] Authorization enforced on the server for every new or changed endpoint (role and ownership); tested with the wrong role/owner.
- [ ] Domain exceptions map to the standard error body with the correct HTTP status; no stack traces in responses.
- [ ] Mutations are transactional; audit events written in the same transaction where the domain model requires them.
- [ ] No path from AI output to authoritative state.

## Tests
- [ ] Unit tests for new domain logic (state machine rows, rules, diff cases).
- [ ] Integration test for new endpoints through the API against the database.
- [ ] E2E updated if the critical journey changed.
- [ ] All tests pass locally and in CI.

## Code quality
- [ ] TypeScript strict, no `any`; Python typed; ruff and ESLint clean; mypy clean for `domain/` and `services/`.
- [ ] Module boundaries respected (api → services → domain/repositories; domain imports nothing from infrastructure).
- [ ] No `console.log`/`print` debugging left; no commented-out code.
- [ ] AI-generated code read in full and compared to the requirement before merge.

## UI (for stories with a screen)
- [ ] Loading, empty, error and success states implemented.
- [ ] Works at 375 px, 768 px and 1280 px without horizontal scroll.
- [ ] Keyboard reachable; visible focus; labels on inputs; colour not the only signal.
- [ ] Role-specific labels shown; no internal status visible to operators.

## Security
- [ ] No secrets committed; `.env.example` updated if a variable was added.
- [ ] Uploads and user content handled per `docs/06-security/THREAT_MODEL.md`.
- [ ] Logs contain identifiers, not payloads or document text.

## Operations and documentation
- [ ] Environment variables documented in `docs/09-operations/OPERATIONS.md` and README if added.
- [ ] Migration included if the schema changed, and it applies on a fresh database.
- [ ] Relevant docs updated (`SCOPE.md` for scope changes, ADR for architecture changes, `CHANGELOG.md` for milestones).
- [ ] Notion story status updated.

## Release-level (end of Day 3)
- [ ] Deployed and health check green.
- [ ] UAT scenarios executed on the deployed URL with results recorded.
- [ ] Production readiness review and assessment traceability completed honestly.
