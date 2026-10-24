"""Nuitka build script for DocForge: compiles Python to native C/machine code.

Prerequisites:
    pip install nuitka
    C compiler (MSVC 2022 or MinGW64)

Usage:
    python build_nuitka.py
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "docforge" / "resources" / "app.ico"
OUTPUT_DIR = ROOT / "dist_nuitka"


def check_nuitka() -> bool:
    try:
        import nuitka  # noqa: F401
        return True
    except ImportError:
        return False


def main() -> None:
    if not check_nuitka():
        print("[-] Nuitka is not installed. Install via:")
        print("    pip install nuitka")
        sys.exit(1)

    print("[*] Starting Nuitka compilation (this may take 5–15 minutes)...")
    t0 = time.perf_counter()

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyqt6",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={ICON}",
        f"--include-data-dir={ICON.parent}=resources",
        f"--include-data-dir={ICON.parent}=docforge/resources",
        "--include-package=docforge",
        "--include-package=markitdown",
        "--include-package=pypandoc",
        "--include-package=pymupdf",
        f"--output-dir={OUTPUT_DIR}",
        "--output-filename=DocForge.exe",
        "main.py",
    ]

    res = subprocess.run(cmd, cwd=str(ROOT))
    t1 = time.perf_counter()

    if res.returncode == 0:
        print(f"[+] Nuitka compilation completed in {t1 - t0:.1f} s")
        print(f"    Output located in: {OUTPUT_DIR}")
    else:
        print(f"[-] Nuitka failed with code {res.returncode}")
        sys.exit(res.returncode)


if __name__ == "__main__":
    main()
