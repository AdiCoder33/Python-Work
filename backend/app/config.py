from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "users.xlsx"
TASKS_FILE = DATA_DIR / "tasks.xlsx"
USERS_LOCK = DATA_DIR / "users.lock"
TASKS_LOCK = DATA_DIR / "tasks.lock"
BACKUPS_DIR = DATA_DIR / "backups"
AUDIT_DIR = DATA_DIR / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.log"
AUDIT_LOCK = DATA_DIR / "audit.lock"

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "480"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
