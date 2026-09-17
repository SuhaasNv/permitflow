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

SEED_USERS = [
    ("operator@permitflow.example.sg", "Tan Wei Ling", Role.OPERATOR),
    ("officer@permitflow.example.sg", "Rahim bin Abdullah", Role.OFFICER),
]


def main() -> None:
    password = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
    with session_factory()() as db:
        repo = UserRepository(db)
        created = 0
        for email, name, role in SEED_USERS:
            if repo.get_by_email(email) is None:
                repo.add(User(email=email, full_name=name, role=role, password_hash=hash_password(password)))
                created += 1
        db.commit()
    print(f"seeded {created} new user(s); {len(SEED_USERS)} total in the seed list")


if __name__ == "__main__":
    main()
