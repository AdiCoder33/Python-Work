import shutil
from datetime import datetime
from pathlib import Path

from filelock import FileLock

from .config import (
    AUDIT_FILE,
    AUDIT_LOCK,
    BACKUPS_DIR,
    TASKS_FILE,
    TASKS_LOCK,
    USERS_FILE,
    USERS_LOCK,
)
from .audit import ensure_audit_file
from .excel_store import ensure_tasks_file, ensure_users_file


def ensure_backup_dir():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def backup_timestamp():
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _copy_with_lock(src: Path, lock_path: Path, dest: Path):
    with FileLock(str(lock_path)):
        if src.exists():
            shutil.copy2(src, dest)


def create_backup_snapshot(include_users=True, include_tasks=True, include_audit=True):
    ensure_backup_dir()
    if include_users:
        ensure_users_file()
    if include_tasks:
        ensure_tasks_file()
    if include_audit:
        ensure_audit_file()

    folder = BACKUPS_DIR / backup_timestamp()
    folder.mkdir(parents=True, exist_ok=True)

    if include_users:
        _copy_with_lock(USERS_FILE, USERS_LOCK, folder / USERS_FILE.name)
    if include_tasks:
        _copy_with_lock(TASKS_FILE, TASKS_LOCK, folder / TASKS_FILE.name)
    if include_audit:
        _copy_with_lock(AUDIT_FILE, AUDIT_LOCK, folder / AUDIT_FILE.name)

    return folder


def prune_backups(retention_days: int):
    if not BACKUPS_DIR.exists():
        return
    dirs = [p for p in BACKUPS_DIR.iterdir() if p.is_dir()]
    dirs_sorted = sorted(dirs, key=lambda p: p.name)
    if retention_days <= 0:
        return
    keep = set(dirs_sorted[-retention_days:])
    for folder in dirs_sorted:
        if folder in keep:
            continue
        shutil.rmtree(folder, ignore_errors=True)


def run_daily_backup(retention_days: int):
    create_backup_snapshot(include_users=True, include_tasks=True, include_audit=True)
    prune_backups(retention_days)


def run_export_backup():
    return create_backup_snapshot(include_users=False, include_tasks=True, include_audit=False)
