import os
import shutil
import subprocess
import sys
from typing import Optional

# Стандартные пути установки MiKTeX — PATH может быть ещё не обновлён
# в текущем процессе после установки через инсталлер
_MIKTEX_DIRS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"),
    r"C:\Program Files\MiKTeX\miktex\bin\x64",
    r"C:\Program Files (x86)\MiKTeX\miktex\bin",
]

# xelatex первым — pdflatex не справляется с кириллицей в Unicode-документах
_ENGINES = ("xelatex", "lualatex", "pdflatex", "tectonic")

# не показывать окно консоли при запуске из pythonw (GUI без терминала)
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

_autoinstall_done = False


def find_pdf_engine() -> Optional[str]:
    """Возвращает полный путь к LaTeX-движку или None."""
    dirs = [d for d in _MIKTEX_DIRS if os.path.isdir(d)]
    for name in _ENGINES:
        path = shutil.which(name)
        if path:
            return path
        for d in dirs:
            candidate = os.path.join(d, name + ".exe")
            if os.path.isfile(candidate):
                return candidate
    return None


def is_unicode_engine(engine_path: str) -> bool:
    """xelatex и lualatex понимают Unicode напрямую (важно для кириллицы)."""
    name = os.path.basename(engine_path).lower()
    return name.startswith(("xelatex", "lualatex"))


def ensure_autoinstall(engine_path: str) -> None:
    """Включает автоустановку недостающих пакетов MiKTeX (один раз за сессию).

    На свежей системе MiKTeX по умолчанию спрашивает перед установкой
    каждого пакета. Pandoc запускает движок неинтерактивно, поэтому без
    этой настройки первая сборка PDF падает с 'package not found'.
    """
    global _autoinstall_done
    if _autoinstall_done:
        return
    initexmf = os.path.join(os.path.dirname(engine_path), "initexmf.exe")
    if not os.path.isfile(initexmf):
        return
    try:
        subprocess.run(
            [initexmf, "--set-config-value", "[MPM]AutoInstall=1"],
            creationflags=_NO_WINDOW, timeout=60,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _autoinstall_done = True
    except Exception:
        pass
