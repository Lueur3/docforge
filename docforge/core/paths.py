"""Работа с путями результата: подбор свободного имени, сравнение путей."""
import itertools
import os
from pathlib import Path


def unique_path(path: str | Path) -> Path:
    """Возвращает путь, которого ещё нет: <имя>-2, <имя>-3 и т.д.

    Работает и для файлов, и для папок (у папки suffix пустой).
    """
    p = Path(path)
    if not p.exists():
        return p
    parent, stem, suffix = p.parent, p.stem, p.suffix
    for n in itertools.count(2):
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("unreachable")  # itertools.count бесконечен


def same_file(a: str | Path, b: str | Path) -> bool:
    """True, если пути указывают на один и тот же файл.

    Сравнение устойчиво к разным написаниям одного пути (слеши, регистр,
    относительные части); samefile дополнительно ловит жёсткие ссылки.
    """
    pa, pb = Path(a), Path(b)
    try:
        if pa.exists() and pb.exists():
            return pa.samefile(pb)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(pa)) == os.path.normcase(os.path.abspath(pb))
