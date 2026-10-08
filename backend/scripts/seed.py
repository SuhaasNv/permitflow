"""Seed demo accounts (idempotent). Run: uv run python scripts/seed.py

The operator and officer passwords come from SEED_PASSWORD (default: the published demonstration
password, shared on purpose). The administrator password comes from SEED_ADMIN_PASSWORD: outside
production it falls back to SEED_PASSWORD so local runs, CI and the browser suite keep working; in
production the script refuses to run without a private value.
"""

import os
import sys
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.infra.db import session_factory  # noqa: E402
from app.models import User  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402

# (email, name, role, protected). Protected accounts (US-073) cannot be changed or deactivated from the
# users page, so the published demonstration sign-ins always work; the spare officer is not protected
# and is the account the admin scenario changes and restores.
SEED_USERS = [
    ("operator@permitflow.example.sg", "Tan Wei Ling", Role.OPERATOR, True),
    ("officer@permitflow.example.sg", "Rahim bin Abdullah", Role.OFFICER, True),
    ("admin@permitflow.example.sg", "Priya Nair", Role.ADMIN, True),
    ("officer2@permitflow.example.sg", "Lim Jun Hao", Role.OFFICER, False),
]
DEMO_PASSWORD = "PermitFlow!2026"


def resolve_passwords(app_env: str, environ: Mapping[str, str]) -> tuple[str, str]:
    """(shared demonstration password, administrator password). Exits non-zero in production unless the
    administrator password is set and is not the published one."""
    password = environ.get("SEED_PASSWORD") or DEMO_PASSWORD
    admin_password = environ.get("SEED_ADMIN_PASSWORD") or ""
    if app_env == "production":
        if not admin_password or admin_password == DEMO_PASSWORD:
            raise SystemExit(
                "refusing to seed in production: set SEED_ADMIN_PASSWORD to a private value "
                "(not unset, not the published demonstration password)."
            )
        return password, admin_password
    return password, admin_password or password


def main() -> None:
    password, admin_password = resolve_passwords(get_settings().app_env, os.environ)
    with session_factory()() as db:
        repo = UserRepository(db)
        created = 0
        for email, name, role, protected in SEED_USERS:
            existing = repo.get_by_email(email)
            if existing is None:
                repo.add(
                    User(
                        email=email,
                        full_name=name,
                        role=role,
                        password_hash=hash_password(admin_password if role == Role.ADMIN else password),
                        is_protected=protected,
                    )
                )
                created += 1
            else:
                # A rerun is the documented reset: role, active flag and protection go back to the
                # seed's values (a scenario that changed the spare account and failed before restoring
                # it is repaired here; review finding, 21 Sep). The password is left alone.
                existing.role = role
                existing.is_active = True
                existing.is_protected = protected
        db.commit()
    print(f"seeded {created} new user(s); {len(SEED_USERS)} total in the seed list")


if __name__ == "__main__":
    main()
