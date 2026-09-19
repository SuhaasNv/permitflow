"""Module boundary rules from ARCHITECTURE.md, enforced by test."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_domain_is_pure_python() -> None:
    for f in (APP / "domain").rglob("*.py"):
        bad = {m for m in _imports(f) if m.split(".")[0] in {"sqlalchemy", "fastapi", "starlette"}}
        bad |= {
            m for m in _imports(f) if m.startswith(("app.models", "app.repositories", "app.infra", "app.api"))
        }
        assert not bad, f"{f.name} imports infrastructure: {bad}"


# The API layer may name these ORM types in annotations (the authenticated user, the loaded application);
# it never queries, constructs or mutates them: that is what the repositories and services are for.
API_MODEL_TYPES = {"User", "Application"}


def _from_imports(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text())
    out: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.update((node.module, a.name) for a in node.names)
    return out


def test_api_does_not_touch_repositories_or_models_directly() -> None:
    for f in (APP / "api").rglob("*.py"):
        bad = {
            m for m in _imports(f) if m == "app.models" or m.startswith(("app.repositories", "app.models."))
        }
        # enums are shared contracts; two model types may be named for annotations (see API_MODEL_TYPES)
        bad -= {"app.models.enums"}
        names = {n for m, n in _from_imports(f) if m == "app.models"}
        if names and names <= API_MODEL_TYPES:
            bad.discard("app.models")
        assert not bad, f"{f.name} imports {bad}"


def test_services_and_schemas_do_not_import_the_api_layer() -> None:
    """Services build responses from `app.schemas`; the API layer is the only one that knows FastAPI."""
    for folder in ("services", "schemas", "repositories"):
        for f in (APP / folder).rglob("*.py"):
            bad = {
                m
                for m in _imports(f)
                if m.startswith("app.api") or m.split(".")[0] in {"fastapi", "starlette"}
            }
            assert not bad, f"{f.name} imports the API layer: {bad}"


def test_schemas_are_free_of_orm_and_io() -> None:
    for f in (APP / "schemas").rglob("*.py"):
        bad = {
            m
            for m in _imports(f)
            if m.startswith(("app.models.", "app.repositories", "app.infra", "app.services"))
        }
        bad = {m for m in bad if m != "app.models.enums"}
        assert not bad, f"{f.name} imports {bad}"


def test_only_verification_service_uses_ai_providers() -> None:
    for f in APP.rglob("*.py"):
        if "infra/ai" in str(f) or f.name == "verification.py":
            continue
        assert not any(m.startswith("app.infra.ai") for m in _imports(f)), f"{f} imports app.infra.ai"


def test_audit_events_are_only_deleted_by_the_draft_purge() -> None:
    """SEC-009: no module updates an AuditEvent; the only delete statement lives in the audit repository."""
    for f in APP.rglob("*.py"):
        src = f.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else ""
            )
            if name not in {"delete", "update"}:
                continue
            args = " ".join(ast.unparse(a) for a in node.args)
            if "AuditEvent" in args:
                assert f == APP / "repositories" / "audit.py" and name == "delete", (
                    f"{f.relative_to(APP)} runs {name}() on AuditEvent"
                )
