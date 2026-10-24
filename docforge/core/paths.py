"""Output path helpers: picking a free name, comparing paths, runtime paths."""
import itertools
import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True if running inside a PyInstaller/Nuitka frozen executable."""
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Return root directory of the application.

    In frozen mode: directory containing the executable.
    In source mode: repository root containing main.py.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_resource_path(relative_name: str) -> Path:
    """Find a resource file (icon, etc.) across source & frozen modes."""
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "resources" / relative_name
        if p.is_file():
            return p

    candidates = [
        app_dir() / "_internal" / "resources" / relative_name,
        app_dir() / "_internal" / "docforge" / "resources" / relative_name,
        app_dir() / "resources" / relative_name,
        app_dir() / "docforge" / "resources" / relative_name,
        Path(__file__).resolve().parents[1] / "resources" / relative_name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def find_bundled_pandoc() -> Path | None:
    """Find bundled pandoc binary and configure PYPANDOC_PANDOC if found."""
    env_p = os.environ.get("PYPANDOC_PANDOC")
    if env_p and Path(env_p).is_file():
        return Path(env_p)

    base = app_dir()
    for candidate in (base / "bin" / "pandoc.exe", base / "pandoc.exe"):
        if candidate.is_file():
            os.environ["PYPANDOC_PANDOC"] = str(candidate)
            return candidate

    system_pandoc = shutil.which("pandoc")
    if system_pandoc:
        return Path(system_pandoc)

    return None


def init_runtime_environment() -> None:
    """Early initialization of runtime paths and environment."""
    find_bundled_pandoc()


def unique_path(path: str | Path, taken: set[str] | None = None) -> Path:
    """Return a path that doesn't exist yet: <name>-2, <name>-3 and so on.

    Works for both files and directories (a directory has an empty suffix).
    `taken` additionally excludes names already reserved elsewhere — a batch
    run uses it so two jobs can't claim the same free name.
    """
    reserved = taken or set()

    def free(p: Path) -> bool:
        return not p.exists() and str(p) not in reserved

    p = Path(path)
    if free(p):
        return p
    parent, stem, suffix = p.parent, p.stem, p.suffix
    for n in itertools.count(2):
        candidate = parent / f"{stem}-{n}{suffix}"
        if free(candidate):
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
