"""Персистентные настройки UI (QSettings — реестр Windows HKCU\\Software\\DocForge)."""
from pathlib import Path

from PyQt6.QtCore import QSettings


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
    """Запоминает папку выбранного файла для следующего диалога «Обзор»."""
    if path:
        put("paths/last_dir", str(Path(path).parent))
