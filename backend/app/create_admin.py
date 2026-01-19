import getpass
from datetime import datetime, timezone
import uuid

from .auth import hash_password
from .excel_store import append_user, ensure_users_file


def main():
    ensure_users_file()
    username = input("Admin username: ").strip()
    if not username:
        print("Username is required.")
        return
    password = getpass.getpass("Admin password: ").strip()
    if not password:
        print("Password is required.")
        return

    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    user_data = {
        "user_id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "role": "admin",
        "is_active": 1,
        "created_at": created_at,
        "last_login_at": "",
    }
    try:
        append_user(user_data)
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print(f"Created admin user: {username}")


if __name__ == "__main__":
    main()
