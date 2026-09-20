# 09 Operations

How the system is run: environments, configuration, deployment, rollback, and the branching rules that decide what reaches which environment. Both documents describe what exists, not a target state; they grew with the stories that added each piece.

| Document | What it holds |
|----------|---------------|
| `OPERATIONS.md` | Local setup, every environment variable, health endpoints, logs, migrations and their compatibility rule, the two Railway environments on the owner's domain, the image tags each runs, the deployment path with the human approval before production, the observability layer (the metrics endpoint, Prometheus, Grafana, the alert rules, the Railway services), rollback by layer (code, schema, data, configuration, prompt, secrets) |
| `BRANCHING.md` | `main` and `dev`, one work branch per story merged with `--no-ff`, the release path (pull request from `dev`, tag, pinned image, approved deploy), hotfixes, branch protection, the rule that every release has a `RELEASE_NOTES.md` entry |

Related: the pipeline design is ADR-009 and ADR-011 in `../03-architecture/decisions/`; the workflows are in `.github/workflows/`; what each version brought is `../../RELEASE_NOTES.md`.
