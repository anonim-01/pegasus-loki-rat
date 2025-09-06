#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure project root is in sys.path for `import app`
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from server.models import db, User
from server.webui import hash_and_salt


def main():
    if len(sys.argv) < 2:
        print("Usage: python server/scripts/update_admin_password.py <NEW_PASSWORD>")
        sys.exit(1)

    new_password = sys.argv[1]

    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        pwd_hash, salt = hash_and_salt(new_password)

        if user is None:
            user = User(username="admin", password=pwd_hash, salt=salt)
            db.session.add(user)
        else:
            user.password = pwd_hash
            user.salt = salt

        db.session.commit()
        print("admin password updated")


if __name__ == "__main__":
    main()
