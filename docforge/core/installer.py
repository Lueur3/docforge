import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from docforge.core import latex
from docforge.proc import NO_WINDOW

log = logging.getLogger(__name__)

# Маркер завершённой первичной настройки (пишется после успешной установки ядра)
MARKER = Path(os.getenv("APPDATA", str(Path.home()))) / "DocForge" / "setup_done"


def module_present(name: str) -> bool:
    """Проверяет установку пакета без его импорта.

    import markitdown тянет onnxruntime/magika и занимает ~1.5 с —
    недопустимо на старте. find_spec проверяет наличие за доли миллисекунды.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def markitdown_installed() -> bool:
    return module_present("markitdown")


def pandoc_installed() -> bool:
    """Полная проверка: пакет pypandoc + доступный бинарник Pandoc.

    Вызывает Pandoc как процесс, поэтому используется только в окне
    настройки, а не на быстром старте."""
    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


class SetupWorker(QThread):
    """Устанавливает выбранные компоненты в фоне."""

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
                f"winget недоступен. Установите компонент вручную (id: {package_id})."
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
                    self.status.emit("Установка MarkItDown с pypi.org...")
                    self._pip("markitdown[all]")
                self.status.emit("Установка pypandoc с pypi.org...")
                self._pip("pypandoc")
                self.status.emit("Установка PyMuPDF с pypi.org...")
                self._pip("pymupdf")
                if not pandoc_installed():
                    self.status.emit("Загрузка Pandoc с github.com/jgm/pandoc (может занять минуту)...")
                    import pypandoc
                    pypandoc.download_pandoc()

            if self._ffmpeg:
                self.status.emit("Установка ffmpeg (imageio-ffmpeg) с pypi.org...")
                self._pip("imageio-ffmpeg")

            if self._miktex:
                self.status.emit("Установка MiKTeX через winget (может занять 5–10 минут)...")
                self._winget("MiKTeX.MiKTeX")
                # включаем автоустановку LaTeX-пакетов, иначе первая
                # сборка PDF падает на неинтерактивном запросе пакета
                engine = latex.find_pdf_engine()
                if engine:
                    latex.ensure_autoinstall(engine)

            if self._chromium:
                self.status.emit("Установка Playwright с pypi.org...")
                self._pip("playwright")
                self.status.emit("Загрузка Chromium (~150 МБ, может занять несколько минут)...")
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
    """Быстрая проверка готовности ядра (без запуска Pandoc)."""
    return MARKER.exists() and module_present("markitdown") and module_present("pypandoc")
