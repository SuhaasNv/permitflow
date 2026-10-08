"""Seed demo accounts (idempotent). Run: uv run python scripts/seed.py

The operator and officer passwords come from SEED_PASSWORD (default: the published demonstration
password, shared on purpose). The administrator password comes from SEED_ADMIN_PASSWORD: outside
production it falls back to SEED_PASSWORD so local runs, CI and the browser suite keep working; in
production the script refuses to run without a private value.

Demo accounts in production are opt-in (US-103). With APP_ENV=production the operator, officer and spare
officer are seeded only when SEED_PUBLIC_DEMO=true (the published default password is then allowed) or when
SEED_PASSWORD is set to a private value; with neither, only the administrator is seeded. An explicit
SEED_PASSWORD equal to the published default without SEED_PUBLIC_DEMO=true is refused. The seed never
removes or re-passwords an account that already exists.
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
TRUTHY = {"1", "true", "yes", "on"}


def public_demo_opted_in(environ: Mapping[str, str]) -> bool:
    """True only for an explicit SEED_PUBLIC_DEMO=true: the published password is then allowed."""
    return environ.get("SEED_PUBLIC_DEMO", "").strip().lower() in TRUTHY


def seed_users_for(app_env: str, environ: Mapping[str, str]) -> list[tuple[str, str, Role, bool]]:
    """The accounts to create. Outside production: all four. In production the demo accounts are opt-in
    (SEED_PUBLIC_DEMO=true, or a private SEED_PASSWORD); without that only the administrator is created."""
    if app_env != "production":
        return list(SEED_USERS)
    shared = environ.get("SEED_PASSWORD") or ""
    if public_demo_opted_in(environ) or (shared and shared != DEMO_PASSWORD):
        return list(SEED_USERS)
    return [user for user in SEED_USERS if user[2] == Role.ADMIN]


def resolve_passwords(app_env: str, environ: Mapping[str, str]) -> tuple[str, str]:
    """(shared demonstration password, administrator password). Exits non-zero in production unless the
    administrator password is set and is not the published one, or when SEED_PASSWORD is explicitly the
    published value without the SEED_PUBLIC_DEMO=true opt-in."""
    password = environ.get("SEED_PASSWORD") or DEMO_PASSWORD
    admin_password = environ.get("SEED_ADMIN_PASSWORD") or ""
    if app_env == "production":
        if environ.get("SEED_PASSWORD") == DEMO_PASSWORD and not public_demo_opted_in(environ):
            raise SystemExit(
                "refusing to seed in production: SEED_PASSWORD is the published demonstration password. "
                "Set a private SEED_PASSWORD, or set SEED_PUBLIC_DEMO=true to opt in to the public demo."
            )
        if not admin_password or admin_password == DEMO_PASSWORD:
            raise SystemExit(
                "refusing to seed in production: set SEED_ADMIN_PASSWORD to a private value "
                "(not unset, not the published demonstration password)."
            )
        return password, admin_password
    return password, admin_password or password


def main() -> None:
    app_env = get_settings().app_env
    password, admin_password = resolve_passwords(app_env, os.environ)
    users = seed_users_for(app_env, os.environ)
    if len(users) < len(SEED_USERS):
        print(
            "production: demo accounts not seeded (SEED_PUBLIC_DEMO=true or a private SEED_PASSWORD opts in)"
        )
    with session_factory()() as db:
        repo = UserRepository(db)
        created = 0
        for email, name, role, protected in users:
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
    print(f"seeded {created} new user(s); {len(users)} total in the seed list")


if __name__ == "__main__":
    main()
