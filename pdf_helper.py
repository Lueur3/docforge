import os
import shutil
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
