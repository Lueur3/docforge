"""Build script for DocForge: creates a standalone onedir distribution.

Usage:
    python build_exe.py
    python build_exe.py --clean
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_FILE = ROOT / "docforge.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
OUTPUT_DIR = DIST_DIR / "DocForge"
OUTPUT_EXE = OUTPUT_DIR / "DocForge.exe"


def clean() -> None:
    print("[*] Cleaning build artifacts...")
    for folder in (BUILD_DIR, DIST_DIR):
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            print(f"    Removed {folder}")


def run_pyinstaller() -> bool:
    print(f"[*] Building DocForge via PyInstaller ({SPEC_FILE.name})...")
    t0 = time.perf_counter()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(SPEC_FILE),
    ]

    res = subprocess.run(cmd, cwd=str(ROOT))
    t1 = time.perf_counter()

    if res.returncode != 0:
        print(f"[-] PyInstaller failed with exit code {res.returncode}")
        return False

    if not OUTPUT_EXE.is_file():
        print(f"[-] Build finished, but {OUTPUT_EXE} not found!")
        return False

    print(f"[+] Build succeeded in {t1 - t0:.1f} s")
    print(f"    Output directory: {OUTPUT_DIR}")
    print(f"    Executable: {OUTPUT_EXE}")

    # calculate total size
    total_bytes = sum(f.stat().st_size for f in OUTPUT_DIR.rglob("*") if f.is_file())
    print(f"    Total dist size: {total_bytes / (1024 * 1024):.1f} MB")
    return True


def check_inno_setup() -> Path | None:
    iscc = shutil.which("iscc")
    if iscc:
        return Path(iscc)

    # Standard 64-bit and 32-bit Program Files locations
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DocForge executable")
    parser.add_argument("--clean", action="store_true", help="Clean build directories first")
    args = parser.parse_args()

    if args.clean:
        clean()

    success = run_pyinstaller()
    if not success:
        sys.exit(1)

    iscc_path = check_inno_setup()
    iss_file = ROOT / "installer.iss"
    if iscc_path and iss_file.is_file():
        print(f"[*] Inno Setup found: {iscc_path}")
        print(f"[*] Compiling installer via {iss_file.name}...")
        res = subprocess.run([str(iscc_path), str(iss_file)], cwd=str(ROOT))
        if res.returncode == 0:
            print("[+] Installer compiled successfully in dist/")
        else:
            print(f"[-] Inno Setup exited with code {res.returncode}")
    else:
        if not iscc_path:
            print("[i] Inno Setup (ISCC.exe) not found. To build setup installer, install Inno Setup 6.")


if __name__ == "__main__":
    main()
