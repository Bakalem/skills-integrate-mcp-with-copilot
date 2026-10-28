"""Create or update a locally stored teacher account."""

import getpass
import hashlib
import json
import secrets
import sys
from pathlib import Path

PASSWORD_HASH_ITERATIONS = 600_000
TEACHERS_FILE = Path(__file__).parent / "teachers.json"
TEACHERS_EXAMPLE_FILE = Path(__file__).parent / "teachers.example.json"


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit("Usage: python src/create_teacher.py <username>")

    username = sys.argv[1].strip()
    password = getpass.getpass("Teacher password (12+ characters): ")
    confirmation = getpass.getpass("Confirm teacher password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters long")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    source = TEACHERS_FILE if TEACHERS_FILE.exists() else TEACHERS_EXAMPLE_FILE
    data = json.loads(source.read_text(encoding="utf-8"))
    teachers = data.get("teachers")
    if not isinstance(teachers, list):
        raise SystemExit(f"Invalid teacher credentials format in {source}")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    ).hex()
    account = {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash,
    }

    for index, teacher in enumerate(teachers):
        if isinstance(teacher, dict) and teacher.get("username") == username:
            teachers[index] = account
            break
    else:
        teachers.append(account)

    TEACHERS_FILE.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )
    TEACHERS_FILE.chmod(0o600)
    print(f"Teacher account '{username}' saved to {TEACHERS_FILE}.")


if __name__ == "__main__":
    main()
