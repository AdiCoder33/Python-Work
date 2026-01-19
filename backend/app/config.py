from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "users.xlsx"
TASKS_FILE = DATA_DIR / "tasks.xlsx"
USERS_LOCK = DATA_DIR / "users.lock"
TASKS_LOCK = DATA_DIR / "tasks.lock"

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "480"))
