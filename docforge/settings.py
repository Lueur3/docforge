"""Persistent UI settings (QSettings — Windows registry HKCU\\Software\\DocForge)."""
import json
import logging
from pathlib import Path

from PyQt6.QtCore import QSettings

log = logging.getLogger(__name__)

RECENT_LIMIT = 10


def _s() -> QSettings:
    return QSettings("DocForge", "DocForge")


def get_bool(key: str, default: bool) -> bool:
    return _s().value(key, default, type=bool)


def get_str(key: str, default: str = "") -> str:
    return _s().value(key, default, type=str)


def get_int(key: str, default: int = 0) -> int:
    return _s().value(key, default, type=int)


def put(key: str, value) -> None:
    _s().setValue(key, value)


def last_dir() -> str:
    return get_str("paths/last_dir", "")


def remember_dir(path: str) -> None:
    """Remember the folder of the chosen file for the next Browse dialog."""
    if path:
        put("paths/last_dir", str(Path(path).parent))


def get_json(key: str, default):
    """Read a JSON-encoded value; falls back to `default` on bad data."""
    raw = get_str(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except ValueError:
        log.warning("Настройки: повреждённое значение %s, используется значение по умолчанию", key)
        return default


def put_json(key: str, value) -> None:
    put(key, json.dumps(value, ensure_ascii=False))


def get_recent(scope: str) -> list[list[str]]:
    """Recent selections for one tab: a list of file lists, newest first."""
    data = get_json(f"recent/{scope}", [])
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, list) and entry]


def push_recent(scope: str, paths: list[str]) -> None:
    """Record a selection, moving a repeat to the top and trimming the tail."""
    if not paths:
        return
    entries = [e for e in get_recent(scope) if e != paths]
    entries.insert(0, list(paths))
    put_json(f"recent/{scope}", entries[:RECENT_LIMIT])
