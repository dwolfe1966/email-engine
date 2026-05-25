"""Create or update an operator user with a hashed password.

Usage:
    python scripts/seed_user.py --email user@example.com \
        --display-name "Some Name" --password 'temp-password'

If --password is omitted you'll get a hidden prompt. The plaintext
password is never written to disk by this script.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from email_platform.db.session import SessionLocal
from email_platform.models.entities import User
from email_platform.services.auth import hash_password


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--email', required=True)
    p.add_argument('--display-name', default='Operator')
    p.add_argument('--role', default='admin')
    p.add_argument('--password', default=None)
    p.add_argument('--inactive', action='store_true')
    args = p.parse_args()

    pw = args.password
    if pw is None:
        pw = getpass.getpass('Password: ')
        confirm = getpass.getpass('Confirm: ')
        if pw != confirm:
            print('Passwords did not match', file=sys.stderr)
            return 1
    if len(pw) < 8:
        print('Password must be at least 8 characters', file=sys.stderr)
        return 1

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == args.email)).scalar_one_or_none()
        hashed = hash_password(pw)
        if user is None:
            db.add(
                User(
                    email=args.email,
                    display_name=args.display_name,
                    role=args.role,
                    password_hash=hashed,
                    is_active=not args.inactive,
                )
            )
            print(f'Created user {args.email} (role={args.role})')
        else:
            user.password_hash = hashed
            user.display_name = args.display_name
            user.role = args.role
            user.is_active = not args.inactive
            user.failed_login_count = 0
            user.locked_until = None
            print(f'Updated user {args.email} (role={args.role})')
        db.commit()
    return 0


if __name__ == '__main__':
    sys.exit(main())
