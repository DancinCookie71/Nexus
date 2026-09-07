#!/usr/bin/env python3
"""Create the first Nexus Panel admin user from the command line."""
from __future__ import annotations

import argparse
import getpass
import sys

from app.auth import create_user
from app.database import SessionLocal, Base, engine
from app.models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first Nexus Panel user.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", help="Admin password (will prompt if omitted)")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1

    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing is not None:
            print(
                f"A user already exists ({existing.username}). "
                "Use the API or database migration tools to add more users.",
                file=sys.stderr,
            )
            return 1

        user = create_user(db, args.username, password)
        print(f"Created user: {user.username} ({user.id})")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
