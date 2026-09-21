"""Seed demo accounts (idempotent). Run: uv run python scripts/seed.py

Passwords come from SEED_PASSWORD (default: "PermitFlow!2026") so they never live in the code path
that ships to production without being set deliberately.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
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


def main() -> None:
    password = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
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
                        password_hash=hash_password(password),
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
