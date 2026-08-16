import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from docforge.core import latex
from docforge.i18n import tr
from docforge.proc import NO_WINDOW

log = logging.getLogger(__name__)

# Marker of a completed first-run setup (written after the core installs)
MARKER = Path(os.getenv("APPDATA", str(Path.home()))) / "DocForge" / "setup_done"


def module_present(name: str) -> bool:
    """Check that a package is installed without importing it.

    `import markitdown` pulls in onnxruntime/magika and costs ~1.5 s — too
    much at startup. find_spec answers in a fraction of a millisecond.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def markitdown_installed() -> bool:
    return module_present("markitdown")


def pandoc_installed() -> bool:
    """Full check: the pypandoc package plus a usable Pandoc binary.

    Spawns Pandoc as a process, so it is only used in the setup dialog,
    never on the fast startup path."""
    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


class SetupWorker(QThread):
    """Installs the selected components in the background."""

    status = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    def __init__(self, core: bool, ffmpeg: bool, miktex: bool, chromium: bool) -> None:
        super().__init__()
        self._core     = core
        self._ffmpeg   = ffmpeg
        self._miktex   = miktex
        self._chromium = chromium

    def _winget(self, package_id: str) -> None:
        if shutil.which("winget") is None:
            raise RuntimeError(
                tr("winget is unavailable. Install the component manually (id: {id}).")
                .format(id=package_id)
            )
        subprocess.check_call(
            ["winget", "install", "--id", package_id, "-e", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
        )

    def _pip(self, package: str) -> None:
        log.info("Установка пакета: %s", package)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
        )

    def run(self) -> None:
        log.info("Настройка: ядро=%s, ffmpeg=%s, miktex=%s, chromium=%s",
                 self._core, self._ffmpeg, self._miktex, self._chromium)
        try:
            if self._core:
                if not markitdown_installed():
                    self.status.emit(tr("Installing MarkItDown from pypi.org..."))
                    self._pip("markitdown[all]")
                self.status.emit(tr("Installing pypandoc from pypi.org..."))
                self._pip("pypandoc")
                self.status.emit(tr("Installing PyMuPDF from pypi.org..."))
                self._pip("pymupdf")
                if not pandoc_installed():
                    self.status.emit(tr("Downloading Pandoc from github.com/jgm/pandoc (may take a minute)..."))
                    import pypandoc
                    pypandoc.download_pandoc()

            if self._ffmpeg:
                self.status.emit(tr("Installing ffmpeg (imageio-ffmpeg) from pypi.org..."))
                self._pip("imageio-ffmpeg")

            if self._miktex:
                self.status.emit(tr("Installing MiKTeX via winget (may take 5–10 minutes)..."))
                self._winget("MiKTeX.MiKTeX")
                # turn on on-the-fly LaTeX package installation, otherwise the
                # first PDF build dies on a non-interactive package prompt
                engine = latex.find_pdf_engine()
                if engine:
                    latex.ensure_autoinstall(engine)

            if self._chromium:
                self.status.emit(tr("Installing Playwright from pypi.org..."))
                self._pip("playwright")
                self.status.emit(tr("Downloading Chromium (~150 MB, may take a few minutes)..."))
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=NO_WINDOW,
                )
        except Exception as e:
            log.exception("Настройка: ошибка установки компонентов")
            self.done.emit(False, str(e))
            return
        log.info("Настройка: установка завершена успешно")
        self.done.emit(True, "")


def mark_setup_done() -> None:
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("ok", encoding="utf-8")


def core_ready() -> bool:
    """Fast check that the core is ready (without spawning Pandoc)."""
    return MARKER.exists() and module_present("markitdown") and module_present("pypandoc")
