"""Create an account from the command line (US-073). Run:

    uv run python scripts/create_user.py --email name@agency.sg --name "Full Name" --role officer

The password is read from CREATE_USER_PASSWORD or prompted for, never passed as an argument (it would
land in the shell history). The same rules as the users page: lower-cased email, at least 12 characters.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.infra.db import session_factory  # noqa: E402
from app.models import User  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402

MIN_PASSWORD = 12


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a PermitFlow account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="the person's full name")
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    parser.add_argument("--protected", action="store_true", help="no admin may change or deactivate it")
    args = parser.parse_args()
    password = os.environ.get("CREATE_USER_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD:
        print(f"the password must be at least {MIN_PASSWORD} characters", file=sys.stderr)
        return 2
    email = args.email.strip().lower()
    with session_factory()() as db:
        repo = UserRepository(db)
        if repo.get_by_email(email) is not None:
            print(f"an account with {email} already exists", file=sys.stderr)
            return 1
        repo.add(
            User(
                email=email,
                full_name=args.name.strip(),
                role=Role(args.role),
                password_hash=hash_password(password),
                is_protected=args.protected,
            )
        )
        db.commit()
    print(f"created {email} as {args.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
