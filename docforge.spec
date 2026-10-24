# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for DocForge (onedir mode)."""
import os
import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).resolve()
icon_file = ROOT / "docforge" / "resources" / "app.ico"

datas = [
    (str(icon_file), "resources"),
    (str(icon_file), "docforge/resources"),
]

binaries = []
# Include bundled pandoc if placed under bin/
bundled_pandoc = ROOT / "bin" / "pandoc.exe"
if bundled_pandoc.is_file():
    binaries.append((str(bundled_pandoc), "bin"))

hidden_imports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "markitdown",
    "pypandoc",
    "fitz",
    "pymupdf",
    "imageio_ffmpeg",
    "pydub",
    "puremagic",
    "charset_normalizer",
    "mammoth",
    "openpyxl",
    "pdfminer",
    "pdfminer.six",
    "bs4",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pytest",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PySide2",
        "PySide6",
        "matplotlib",
        "scipy",
        "IPython",
        "zmq",
        "tornado",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DocForge",
)
