"""Output path helpers: picking a free name, comparing paths."""
import itertools
import os
from pathlib import Path


def unique_path(path: str | Path) -> Path:
    """Return a path that doesn't exist yet: <name>-2, <name>-3 and so on.

    Works for both files and directories (a directory has an empty suffix).
    """
    p = Path(path)
    if not p.exists():
        return p
    parent, stem, suffix = p.parent, p.stem, p.suffix
    for n in itertools.count(2):
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("unreachable")  # itertools.count is infinite


def same_file(a: str | Path, b: str | Path) -> bool:
    """True if both paths point at the same file.

    The comparison tolerates different spellings of one path (slashes, case,
    relative parts); samefile additionally catches hard links.
    """
    pa, pb = Path(a), Path(b)
    try:
        if pa.exists() and pb.exists():
            return pa.samefile(pb)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(pa)) == os.path.normcase(os.path.abspath(pb))
