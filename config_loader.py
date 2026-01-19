import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SUBDIVISIONS_FILE = CONFIG_DIR / "subdivisions.json"
TEMPLATES_FILE = CONFIG_DIR / "templates.json"

DEFAULT_SUBDIVISIONS = ["RKV SubDiv-1", "RKV SubDiv-2", "RKV SubDiv-3"]
DEFAULT_TEMPLATES = {
    "Blank": {},
    "Spill Default": {"account_code": "Spill"},
    "New Default": {"account_code": "New"},
    "Monthly Repeat": {
        "exp_upto_last_month": 0,
        "exp_during_this_month": 0,
        "works_completed": 0,
    },
}


def _load_json(path: Path):
    try:
        data = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def load_subdivisions():
    data = _load_json(SUBDIVISIONS_FILE)
    if not isinstance(data, dict):
        return list(DEFAULT_SUBDIVISIONS)
    subdivisions = data.get("subdivisions")
    if not isinstance(subdivisions, list):
        return list(DEFAULT_SUBDIVISIONS)
    cleaned = [str(item).strip() for item in subdivisions if str(item).strip()]
    return cleaned or list(DEFAULT_SUBDIVISIONS)


def load_templates():
    data = _load_json(TEMPLATES_FILE)
    if not isinstance(data, dict):
        return dict(DEFAULT_TEMPLATES)
    templates = data.get("templates")
    if not isinstance(templates, dict):
        return dict(DEFAULT_TEMPLATES)
    cleaned = {}
    for name, values in templates.items():
        if not str(name).strip():
            continue
        if isinstance(values, dict):
            cleaned[str(name)] = values
    return cleaned or dict(DEFAULT_TEMPLATES)
