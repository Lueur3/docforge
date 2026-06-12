import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QLabel,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)

import ffmpeg_helper
import pdf_helper

_MARKER = Path(os.getenv("APPDATA", str(Path.home()))) / "DocForge" / "setup_done"


def _markitdown_installed() -> bool:
    try:
        import markitdown  # noqa: F401
        return True
    except ImportError:
        return False


def _pandoc_installed() -> bool:
    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


class _SetupWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    def __init__(self, core: bool, ffmpeg: bool, miktex: bool) -> None:
        super().__init__()
        self._core   = core
        self._ffmpeg = ffmpeg
        self._miktex = miktex

    def _pip(self, package: str) -> None:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def run(self) -> None:
        try:
            if self._core:
                if not _markitdown_installed():
                    self.status.emit("Установка MarkItDown с pypi.org...")
                    self._pip("markitdown[all]")
                self.status.emit("Установка pypandoc с pypi.org...")
                self._pip("pypandoc")
                if not _pandoc_installed():
                    self.status.emit("Загрузка Pandoc с github.com/jgm/pandoc (может занять минуту)...")
                    import pypandoc
                    pypandoc.download_pandoc()

            if self._ffmpeg:
                self.status.emit("Установка ffmpeg (imageio-ffmpeg) с pypi.org...")
                self._pip("imageio-ffmpeg")

            if self._miktex:
                if shutil.which("winget") is None:
                    raise RuntimeError(
                        "winget недоступен. Установите MiKTeX вручную: https://miktex.org"
                    )
                self.status.emit("Установка MiKTeX через winget (может занять 5–10 минут)...")
                subprocess.check_call(
                    ["winget", "install", "--id", "MiKTeX.MiKTeX", "-e", "--silent",
                     "--accept-package-agreements", "--accept-source-agreements"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            self.done.emit(False, str(e))
            return
        self.done.emit(True, "")


class SetupDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocForge — настройка компонентов")
        self.setMinimumWidth(540)

        core_ok   = _markitdown_installed() and _pandoc_installed()
        ffmpeg_ok = ffmpeg_helper.find_ffmpeg() is not None
        miktex_ok = pdf_helper.find_pdf_engine() is not None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        intro = QLabel(
            "DocForge использует внешние компоненты. Ниже показано, что и откуда "
            "будет загружено. Необязательные компоненты можно отключить."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(8)

        self._chk_core = self._add_row(
            layout,
            "MarkItDown + Pandoc — ядро конвертации",
            "pypi.org/project/markitdown · pypi.org/project/pypandoc · github.com/jgm/pandoc/releases",
            installed=core_ok, required=True,
        )
        self._chk_ffmpeg = self._add_row(
            layout,
            "ffmpeg — аудио и видео во вкладке MarkItDown",
            "pypi.org/project/imageio-ffmpeg (~30 МБ)",
            installed=ffmpeg_ok, required=False,
        )
        self._chk_miktex = self._add_row(
            layout,
            "MiKTeX — вывод в PDF во вкладке Pandoc",
            "winget: MiKTeX.MiKTeX, источник miktex.org (~250 МБ)",
            installed=miktex_ok, required=False,
        )

        layout.addSpacing(8)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.hide()
        layout.addWidget(self._bar)

        nothing_to_install = core_ok and ffmpeg_ok and miktex_ok
        self._btn = QPushButton("Продолжить" if nothing_to_install else "Установить и продолжить")
        self._btn.setFixedHeight(34)
        self._btn.clicked.connect(self._start)
        layout.addWidget(self._btn)

        self._worker: _SetupWorker | None = None

    def _add_row(self, layout: QVBoxLayout, title: str, source: str,
                 installed: bool, required: bool) -> QCheckBox:
        chk = QCheckBox()
        if installed:
            chk.setText(f"{title}  —  ✓ уже установлено")
            chk.setChecked(True)
            chk.setEnabled(False)
        elif required:
            chk.setText(f"{title}  —  обязательно")
            chk.setChecked(True)
            chk.setEnabled(False)
        else:
            chk.setText(title)
            chk.setChecked(True)
        chk.setProperty("installed", installed)
        layout.addWidget(chk)

        src = QLabel(f"Источник: {source}")
        src.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px;")
        src.setWordWrap(True)
        layout.addWidget(src)
        return chk

    def _start(self) -> None:
        core   = not self._chk_core.property("installed")
        ffmpeg = self._chk_ffmpeg.isChecked() and not self._chk_ffmpeg.property("installed")
        miktex = self._chk_miktex.isChecked() and not self._chk_miktex.property("installed")

        if not (core or ffmpeg or miktex):
            self._finish()
            return

        for chk in (self._chk_core, self._chk_ffmpeg, self._chk_miktex):
            chk.setEnabled(False)
        self._btn.setEnabled(False)
        self._bar.show()

        self._worker = _SetupWorker(core, ffmpeg, miktex)
        self._worker.status.connect(self._status.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool, error: str) -> None:
        if not success:
            QMessageBox.warning(self, "Ошибка установки", error)
            if not (_markitdown_installed() and _pandoc_installed()):
                sys.exit(1)
        self._finish()

    def _finish(self) -> None:
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.write_text("ok", encoding="utf-8")
        self.accept()


def ensure_dependencies(_app: QApplication) -> None:
    """Показывает окно настройки при первом запуске или если ядро не установлено."""
    if _MARKER.exists() and _markitdown_installed() and _pandoc_installed():
        return
    SetupDialog().exec()
