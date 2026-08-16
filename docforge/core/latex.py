import logging
import os
import shutil
import subprocess
from typing import Optional

from docforge.proc import NO_WINDOW

log = logging.getLogger(__name__)

# Standard MiKTeX install locations — PATH may not be refreshed in the current
# process yet right after the installer has run
_MIKTEX_DIRS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"),
    r"C:\Program Files\MiKTeX\miktex\bin\x64",
    r"C:\Program Files (x86)\MiKTeX\miktex\bin",
]

# xelatex first — pdflatex cannot handle Cyrillic in Unicode documents
_ENGINES = ("xelatex", "lualatex", "pdflatex", "tectonic")

_autoinstall_done = False


def find_pdf_engine() -> Optional[str]:
    """Return the full path to a LaTeX engine, or None."""
    dirs = [d for d in _MIKTEX_DIRS if os.path.isdir(d)]
    for name in _ENGINES:
        path = shutil.which(name)
        if path:
            log.info("PDF-движок найден в PATH: %s", path)
            return path
        for d in dirs:
            candidate = os.path.join(d, name + ".exe")
            if os.path.isfile(candidate):
                log.info("PDF-движок найден: %s", candidate)
                return candidate
    log.info("PDF-движок не найден (проверены PATH и %s)", dirs)
    return None


def is_unicode_engine(engine_path: str) -> bool:
    """xelatex and lualatex understand Unicode natively (matters for Cyrillic)."""
    name = os.path.basename(engine_path).lower()
    return name.startswith(("xelatex", "lualatex"))


def ensure_autoinstall(engine_path: str) -> None:
    """Enable on-the-fly MiKTeX package installation (once per session).

    On a fresh system MiKTeX asks before installing each package. Pandoc runs
    the engine non-interactively, so without this the first PDF build fails
    with 'package not found'.
    """
    global _autoinstall_done
    if _autoinstall_done:
        return
    initexmf = os.path.join(os.path.dirname(engine_path), "initexmf.exe")
    if not os.path.isfile(initexmf):
        log.debug("initexmf не найден рядом с %s — пропуск автоустановки", engine_path)
        return
    try:
        subprocess.run(
            [initexmf, "--set-config-value", "[MPM]AutoInstall=1"],
            creationflags=NO_WINDOW, timeout=60,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _autoinstall_done = True
        log.info("MiKTeX: включена автоустановка пакетов (AutoInstall=1)")
    except Exception:
        log.exception("MiKTeX: не удалось включить автоустановку пакетов")
