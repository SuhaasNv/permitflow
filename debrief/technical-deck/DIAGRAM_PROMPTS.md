# Diagram prompts for the technical deck

Five diagrams, one prompt each. Every prompt is self-contained: paste the template image first, then the prompt. All names below are the real names from the codebase, the workflows and the Railway project as of 19 September 2026 (v0.3.0). Do not let the generator invent components: if it adds Redis, Kubernetes, a message queue, a CDN, a load balancer or a second replica, the diagram is wrong.

Shared instruction, put at the top of every prompt:

> Follow the attached template exactly: same box shapes, same colour palette, same line style, same font, same legend position, same title placement. Landscape 16:9. Use exactly the names given below, spelled as given. No emoji, no gradients, no icons that are not in the template. No em dashes anywhere; use a colon or a comma. Do not add components that are not listed. Leave enough white space that the text is readable at slide size.

Acceptance rules I will use when rating each diagram follow each prompt.

Outcome (19 Sep 2026): diagrams 1, 4 and 5 were accepted and live in `docs/architecture/diagrams/views/` as `solution-architecture.png`, `deployment.png` and `ci-cd-pipeline.png`. Diagram 2 was skipped (the layering is in `docs/architecture/ARCHITECTURE.md` as text) and diagram 3 was dropped after three attempts kept mis-routing the browser-to-API and OpenAI arrows. The working names during generation were:

- `01-solution-architecture.png`
- `02-logical-architecture.png`
- `03-physical-architecture.png`
- `04-deployment.png`
- `05-ci-cd-pipeline.png`



---

## 1. Solution architecture

**What this diagram is:** the system in context. Who uses it, what the system is made of at the module level, what it stores, and what it depends on outside. One picture that a non-engineer and an engineer both read in a minute. No layers, no ports, no hosting.

**Prompt:**

> Draw a solution architecture diagram titled "PermitFlow: solution architecture" for a regulatory licensing platform (Singapore Food Establishment Licence). Three zones from left to right: Users, PermitFlow system, External services.
>
> Users zone, three actors: "Operator (business applicant)", "Licensing officer", "Admin (read-only oversight, planned v0.4.0)". All three use a web browser. Show one arrow from the browser to the system labelled "HTTPS, JSON API, JWT bearer token".
>
> PermitFlow system zone, a large container with two boxes inside.
>
> Box "Web application (React 19, TypeScript strict, Vite)" with these feature areas listed inside: Landing and legal pages; Sign in; Operator: dashboard, application form (sections and uploads), submission, resubmission, history; Officer: queue, case review, feedback, compare revisions, audit trail, licence preview; Notifications.
>
> Box "API (FastAPI, Python 3.12)" showing nine modules as small boxes in a grid: Auth (JWT, roles); Applications (draft, sections, submit); Revisions (immutable snapshots, compare); Documents (upload, allowlist, magic bytes, 10 MB); AI verification (background task per document); Feedback (templates, targets, resolution); Workflow (state machine, 14 statuses, role labels); Notifications; Audit (append-only); Licence (PDF certificate on approval). Add a small note on the API box: "Every status change goes through the state machine. The AI check advises the officer and never changes status."
>
> Below the API, inside the system zone, two data stores: "PostgreSQL (relational tables plus JSON snapshots per revision)" and "File storage (uploads volume, server-generated keys)". Arrows from the API to both.
>
> External services zone, two boxes: "OpenAI API (gpt-4.1-mini, structured output, 30 s timeout, one retry)" with an arrow from the AI verification module labelled "document text, strict schema"; and "LangSmith (optional tracing of AI runs, inputs hidden)" with a dashed arrow from the AI verification module labelled "traces, when configured".
>
> Legend: solid arrow = synchronous call, dashed arrow = optional or asynchronous.

**Rating rules:**
- Three actors, admin marked planned.
- Web application and API as two separate boxes; browser talks to the API directly (no server-side rendering, no proxy box).
- Nine modules named as above; Workflow and AI verification present; the advisory note present.
- Exactly two data stores and two external services. No queue, no cache, no email service.
- Arrow to OpenAI leaves the AI verification module only.

---

## 2. Logical architecture

**What this diagram is:** the layers inside the code and the direction dependencies are allowed to point. This is the diagram behind ADR-001 (modular monolith) and the layering test. No hosting, no external services except as a leaf.

**Prompt:**

> Draw a logical architecture diagram titled "PermitFlow: logical architecture (modular monolith, dependency direction)". Two columns: "Frontend (frontend/src)" on the left, "Backend (backend/app)" on the right, with a single arrow between them labelled "REST /api/v1, JSON, Bearer JWT".
>
> Frontend column, four horizontal layers from top to bottom, arrows pointing downward only:
> 1. "app/: router, providers (QueryClient, Auth), layout shell"
> 2. "features/: auth, operator, officer, admin, landing, legal, shared components"
> 3. "api/: typed client, hand-written types mirroring the API schemas, error mapping"
> 4. "lib/ and domain/: zod schema builder from /form-schema, labels, formatting"
> Note beside the column: "Server state in TanStack Query; forms with React Hook Form and Zod; polling every 2 s while a document check is running."
>
> Backend column, layers from top to bottom with arrows pointing downward only:
> 1. "api/v1: routers (auth, applications, officer, notifications, form_schema, health), dependencies: current user, role, ownership; maps exceptions to the error envelope { error: { code, message, details } }"
> 2. "services: use cases, one method = one transaction. applications, submission, resubmission, documents, verification, feedback, workflow, licence, withdrawal, notifications, audit_trail, quotas, officer_queue, officer_view, operator_view, compare, draft_deletion"
> 3. "domain: pure Python, no I/O. workflow (state machine table), labels (role labels), diff, editability, resolution, completeness, uploads, verification_rules, feedback_templates, licence, form_schema"
> 4. Two side-by-side boxes on the same level: "repositories: SQLAlchemy queries, ownership filters" and "schemas: Pydantic request and response models"
> 5. "models: SQLAlchemy ORM (users, applications, application_revisions, documents, verification_runs, feedback, notifications, audit_events, licences)"
> To the right of the backend layers, a tall vertical box "infra: settings, db session, storage (FileStorage), extraction (pypdf), pdf, ai (VerificationProvider: OpenAI provider, Mock provider, tracing)" with an arrow from services into it, and one dashed arrow from "infra.ai" out of the diagram labelled "OpenAI API".
>
> Rules box at the bottom, four lines:
> - "api never imports repositories or models; it calls services."
> - "domain imports nothing from below: no SQLAlchemy, no FastAPI, no I/O."
> - "services.verification is the only caller of infra.ai."
> - "A unit test enforces the layering."
>
> Colour the domain layer in the template's accent colour to show it is the core.

**Rating rules:**
- Arrows point one way only (top to bottom); no arrow from domain to anything below it.
- repositories and schemas sit on the same level; models below them.
- infra is beside the stack, not a layer inside it.
- Domain highlighted. Rules box present with all four lines.
- Frontend has four layers, no Redux, no Next.js, no server components.

---

## 3. Physical architecture

**What this diagram is:** the runtime: which processes run where, on which ports, over which protocol, with which hostnames, and what is separate between environments. This is the picture for "what is actually running when a reviewer opens the URL".

**Prompt:**

> Draw a physical architecture diagram titled "PermitFlow: physical architecture (Railway, two environments that share nothing)".
>
> Left: a box "User's browser" with an arrow labelled "HTTPS 443, TLS by Railway" to the right.
>
> Middle: a box "DNS: permitflow.space at Namecheap (ALIAS at the apex, CNAMEs for the rest, one TXT verification record per hostname)".
>
> Right: a large container "Railway project permitflow, region us-west2" containing two identical environment boxes stacked vertically: "Environment: production (from main)" on top and "Environment: development (from dev)" below. Each environment box contains four nodes:
> - "frontend container: nginx 1.27 alpine, port 8080. Serves the Vite build, /healthz, /config.js (API URL written at container start from API_URL), security headers and a Content Security Policy generated from the API origin."
> - "backend container: python 3.12 slim, uvicorn, port 8000. Runs alembic upgrade head on start. /api/v1/health returns 503 when the database ping fails. Rate limits and sign-in limits in process."
> - "PostgreSQL 18 service (private network only)"
> - "Volume uploads mounted at /data/uploads on the backend"
> Arrows inside each environment: browser to frontend (static files), browser to backend (JSON API; the browser calls the API directly, the frontend does not proxy), backend to PostgreSQL (private network, psycopg), backend to volume.
> Hostnames on the boxes: production frontend "permitflow.space, www.permitflow.space", production API "api.permitflow.space"; development frontend "dev.permitflow.space", development API "api.dev.permitflow.space".
> A thick horizontal separator between the two environments with the text "Separate database, volume, secrets, tokens and domains. Nothing is shared."
>
> Far right, outside Railway: "OpenAI API (gpt-4.1-mini)" with an arrow from each backend, and "LangSmith (tracing, development only)" with a dashed arrow from the development backend only.
>
> Bottom note: "One replica per service, single region, no blue/green: Railway keeps the old container answering until the new one passes its health check."
>
> Legend: solid = HTTPS, dotted = private network, dashed = optional.

**Rating rules:**
- Exactly two environments, both with all four nodes; PostgreSQL 18, not 16 (16 is the local Compose image only).
- Browser calls the backend directly; the frontend has no proxy arrow to the backend.
- Ports 8080 and 8000 present; uploads path present.
- LangSmith arrow from development only.
- No load balancer, CDN, Redis, worker or second region.

---

## 4. Deployment diagram

**What this diagram is:** which artefacts land on which nodes, from which branch, with which tags, and what configuration each node needs. The physical diagram shows the hosts; this one shows what is put on them and how a release is promoted and rolled back.

**Prompt:**

> Draw a deployment diagram titled "PermitFlow: deployment (build once, promote by tag, production behind a person)".
>
> Left column "Source": a box "GitHub repository suhaasnv/permitflow" with two branch lanes: "dev (integration, default branch)" and "main (releases only, tag v0.<sprint>.0, current v0.3.0)". A small note: "Story branches feat/us-xxx merge into dev with --no-ff; main receives releases only."
>
> Middle column "Artefacts": a box "GitHub Container Registry (GHCR, public packages)" containing two image boxes: "ghcr.io/suhaasnv/permitflow-backend" and "ghcr.io/suhaasnv/permitflow-frontend". Under each, the tags: "sha-<short commit>", "dev or main (branch)", "v0.3.0 (on main only, from frontend/package.json)". Arrow from the repository to GHCR labelled "CI images job, only after every other job is green; pull requests build but never push".
>
> Right column "Targets": two boxes, "Railway environment development" and "Railway environment production". Each contains "backend service" and "frontend service" with the image tag they pull: development pulls ":dev", production pulls ":main". Each also lists its configuration: backend "DATABASE_URL, JWT_SECRET (distinct per environment), CORS_ORIGINS, UPLOAD_DIR=/data/uploads, TRUSTED_PROXIES, AI_PROVIDER=openai, OPENAI_API_KEY, OPENAI_MODEL, LANGSMITH_* (optional)"; frontend "API_URL, PORT=8080". Below each environment: "PostgreSQL 18" and "volume uploads".
>
> Arrows from GHCR to the two environments labelled "railway redeploy pulls the tag (Railway never builds)".
>
> Two gate symbols on the production arrow, in order: "GitHub environment production: required reviewer approval (repository owner), main only" and "Post-deploy gates: /api/v1/health, /healthz, config.js names this environment's API; about seven minutes". One gate symbol on the development arrow: "Post-deploy gates" only.
>
> Note under the production box: "Deploy job for production is started by hand: gh workflow run deploy.yml --ref main -f environment=production, after CI is green on main."
>
> A "Rollback" callout at the bottom right: "Point the service at the previous sha- or v tag in Railway and redeploy. Migrations are forward-only."
>
> A "Seeding" callout: "scripts/seed.py run once per environment by hand (two demo accounts). A deploy never touches data."

**Rating rules:**
- Two images, three tag kinds, `v` tag on main only.
- Development pulls `:dev`, production pulls `:main`.
- Approval gate on production only; health gates on both.
- Manual production dispatch note present.
- Rollback and seeding callouts present. No "Railway builds from repo" arrow.

---

## 5. GitHub CI/CD pipeline

**What this diagram is:** the flow of one push through the four workflows: `ci.yml` (seven jobs), `ai-gate.yml` (called by CI, six jobs), `deploy.yml`, and `ai-eval.yml` (nightly and on AI-path pushes). Left to right, with the job dependencies exact.

**Prompt:**

> Draw a CI/CD pipeline diagram titled "PermitFlow: CI/CD (GitHub Actions, four workflows)". Flow left to right.
>
> Trigger box on the far left: "push or pull request to dev or main".
>
> Workflow lane 1, "ci.yml (CI)". Five jobs start in parallel as a vertical stack:
> - "Backend: ruff, mypy strict, pytest on a PostgreSQL service, coverage summary"
> - "Frontend: eslint, tsc, vitest with coverage thresholds, vite build"
> - "AI gate: calls ai-gate.yml" (draw this as a box that expands into lane 2)
> - "Secret scan: gitleaks over the full history"
> - "Dependency and code audit: pip-audit (blocking), bandit at medium (blocking), npm audit at high (blocking)"
> A sixth job "End to end: PostgreSQL service, alembic upgrade head, seed, uvicorn on :8000 with AI_PROVIDER=mock, vite preview on :3000, Playwright journey plus six scenarios plus axe accessibility gate; rate limits set to 0" placed to the right of Backend and Frontend with arrows from both ("needs: backend, frontend").
> A seventh job "Images: build both Docker images; push to GHCR with tags sha-<commit>, branch, and v<version> on main; pull requests never push" to the right with arrows from all six jobs ("needs: all").
>
> Workflow lane 2, "ai-gate.yml (reusable, workflow_call only, mock provider, blocking)", drawn as a sub-pipeline under the AI gate job: five parallel jobs "Model approval", "Contracts (PostgreSQL service)", "Golden set (14 cases)", "Adversarial (prompt injection cases)", "Fairness (7 name sets x 3 scenarios, 21 runs)", all feeding one job "Verdict".
>
> Workflow lane 3, "deploy.yml (Deploy)". Trigger: "workflow_run: CI completed with success on a push" and "workflow_dispatch: choose environment". Steps in order: "Pre-deploy gate: run is the head of the branch", "Install Railway CLI", "railway redeploy backend and frontend from the new images", "Wait for the NEW deployment of each service to be SUCCESS", "Post-deploy gate: /api/v1/health and /healthz answer 200", "Post-deploy gate: config.js names this environment's API". Two branches out of the trigger: "dev: environment development, no approval" and "main: environment production, required reviewer approval; started by hand with --ref main because workflow_run executes on the default branch". Arrow from the Images job to this lane.
>
> Workflow lane 4, "ai-eval.yml (AI evaluation, live)". Triggers: "nightly 04:00 Singapore", "manual", "push to dev or main touching the AI module or the set". One job "Live: golden set and fairness against the real OpenAI model, blocking at 14 of 14, LangSmith experiment recorded when the key is present, fails loudly when OPENAI_API_KEY is missing".
>
> Legend: green box = blocking job, grey box = reporting only. All jobs in this pipeline are blocking except none: mark them all green and state "every job blocks the images".
>
> Bottom note: "All workflows run with shell: bash (pipefail). Images are built once and deployed unchanged."

**Rating rules:**
- CI has seven jobs with the stated dependencies: E2E needs Backend and Frontend; Images needs all six.
- AI gate expands to five parallel jobs plus Verdict; runs on the mock provider.
- Deploy: two triggers, the six steps in order, approval on production only, manual production note present.
- AI evaluation is a separate lane with its three triggers and the 14 of 14 rule.
- No CodeQL, Semgrep, Trivy, promptfoo, SonarQube or staging environment (those are listed as next steps, not built).

---

## Optional 6 and 7 (already in the repository as text; only if the deck wants pictures)

- **State machine** (`docs/architecture/STATE_MACHINE.md`): 14 statuses, transitions with actor and guard, three terminal states, role labels. A prompt can be written from that table if wanted; the exact transition list must be copied from the file, not summarised.
- **Domain model** (`docs/architecture/DOMAIN_MODEL.md`): User, Application, ApplicationRevision, Document, VerificationRun, Feedback, Notification, AuditEvent, Licence, with the cardinalities shown in the entity overview.
