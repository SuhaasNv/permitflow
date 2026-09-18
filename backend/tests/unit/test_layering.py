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


def test_api_does_not_touch_repositories_or_models_directly() -> None:
    for f in (APP / "api").rglob("*.py"):
        bad = {m for m in _imports(f) if m.startswith(("app.repositories", "app.models."))}
        # enums are shared contracts and may be imported by the API layer
        bad = {m for m in bad if m != "app.models.enums"}
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
