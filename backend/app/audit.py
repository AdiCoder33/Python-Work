import json
import os
from datetime import datetime, timezone

from filelock import FileLock

from .config import AUDIT_DIR, AUDIT_FILE, AUDIT_LOCK


def ensure_audit_file():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.touch()


def log_event(
    action: str,
    actor: str,
    role: str,
    status: str,
    metadata: dict | None,
    trace_id: str,
    ip: str,
    user_agent: str,
    ts: str | None = None,
):
    ensure_audit_file()
    timestamp = ts or datetime.now(timezone.utc).isoformat()
    event = {
        "ts": timestamp,
        "action": action,
        "actor": actor or "",
        "role": role or "",
        "status": status,
        "metadata": metadata or {},
        "trace_id": trace_id or "",
        "ip": ip or "",
        "user_agent": user_agent or "",
    }
    payload = json.dumps(event, default=str, separators=(",", ":"))
    with FileLock(str(AUDIT_LOCK)):
        with open(AUDIT_FILE, "a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
            handle.flush()
            os.fsync(handle.fileno())
