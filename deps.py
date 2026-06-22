import importlib.util
import logging
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

log = logging.getLogger(__name__)

_MARKER = Path(os.getenv("APPDATA", str(Path.home()))) / "DocForge" / "setup_done"

# не показывать окно консоли при запуске из pythonw (GUI без терминала)
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _module_present(name: str) -> bool:
    """Проверяет установку пакета без его импорта.

    import markitdown тянет onnxruntime/magika и занимает ~1.5 с —
    недопустимо на старте. find_spec проверяет наличие за доли миллисекунды.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _markitdown_installed() -> bool:
    return _module_present("markitdown")


def _pandoc_installed() -> bool:
    """Полная проверка: пакет pypandoc + доступный бинарник Pandoc.

    Вызывает Pandoc как процесс, поэтому используется только в окне
    настройки, а не на быстром старте."""
    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


class _SetupWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    def __init__(self, core: bool, ffmpeg: bool, miktex: bool, wkhtmltopdf: bool) -> None:
        super().__init__()
        self._core        = core
        self._ffmpeg      = ffmpeg
        self._miktex      = miktex
        self._wkhtmltopdf = wkhtmltopdf

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
            creationflags=_NO_WINDOW,
        )

    def _pip(self, package: str) -> None:
        log.info("Установка пакета: %s", package)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )

    def run(self) -> None:
        log.info("Настройка: ядро=%s, ffmpeg=%s, miktex=%s, wkhtmltopdf=%s",
                 self._core, self._ffmpeg, self._miktex, self._wkhtmltopdf)
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
                self.status.emit("Установка MiKTeX через winget (может занять 5–10 минут)...")
                self._winget("MiKTeX.MiKTeX")
                # включаем автоустановку LaTeX-пакетов, иначе первая
                # сборка PDF падает на неинтерактивном запросе пакета
                engine = pdf_helper.find_pdf_engine()
                if engine:
                    pdf_helper.ensure_autoinstall(engine)

            if self._wkhtmltopdf:
                self.status.emit("Установка wkhtmltopdf через winget...")
                self._winget("wkhtmltopdf.wkhtmltox")
        except Exception as e:
            log.exception("Настройка: ошибка установки компонентов")
            self.done.emit(False, str(e))
            return
        log.info("Настройка: установка завершена успешно")
        self.done.emit(True, "")


class SetupDialog(QDialog):
    def __init__(self, first_run: bool = True) -> None:
        super().__init__()
        self._first_run = first_run
        self.setWindowTitle(
            "DocForge — настройка компонентов" if first_run else "DocForge — компоненты"
        )
        self.setMinimumWidth(540)

        core_ok   = _markitdown_installed() and _pandoc_installed()
        ffmpeg_ok = ffmpeg_helper.find_ffmpeg() is not None
        miktex_ok = pdf_helper.find_pdf_engine() is not None
        wkhtml_ok = pdf_helper.find_wkhtmltopdf() is not None

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
            "MiKTeX — вывод в PDF во вкладке Pandoc (движок LaTeX)",
            "winget: MiKTeX.MiKTeX, источник miktex.org (~250 МБ)",
            installed=miktex_ok, required=False,
        )
        self._chk_wkhtml = self._add_row(
            layout,
            "wkhtmltopdf — PDF «как веб-страница» (браузерный движок)",
            "winget: wkhtmltopdf.wkhtmltox (~70 МБ)",
            installed=wkhtml_ok, required=False,
        )

        layout.addSpacing(8)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.hide()
        layout.addWidget(self._bar)

        nothing_to_install = core_ok and ffmpeg_ok and miktex_ok and wkhtml_ok
        if nothing_to_install:
            self._btn = QPushButton("Продолжить" if first_run else "Закрыть")
        else:
            self._btn = QPushButton("Установить и продолжить" if first_run else "Установить")
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
        wkhtml = self._chk_wkhtml.isChecked() and not self._chk_wkhtml.property("installed")

        if not (core or ffmpeg or miktex or wkhtml):
            self._finish()
            return

        for chk in (self._chk_core, self._chk_ffmpeg, self._chk_miktex, self._chk_wkhtml):
            chk.setEnabled(False)
        self._btn.setEnabled(False)
        self._bar.show()

        self._worker = _SetupWorker(core, ffmpeg, miktex, wkhtml)
        self._worker.status.connect(self._status.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool, error: str) -> None:
        if not success:
            QMessageBox.warning(self, "Ошибка установки", error)
            # критично выйти только если на первом запуске не встало ядро
            if self._first_run and not (_markitdown_installed() and _pandoc_installed()):
                sys.exit(1)
            self._btn.setEnabled(True)
            return
        # ffmpeg мог только что установиться — подключаем его к pydub сразу
        path = ffmpeg_helper.find_ffmpeg()
        if path:
            ffmpeg_helper.configure_pydub(path)
        self._finish()

    def _finish(self) -> None:
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.write_text("ok", encoding="utf-8")
        self.accept()


def open_components_dialog() -> None:
    """Открывает диалог компонентов в режиме управления (не первый запуск)."""
    log.info("Открытие диалога компонентов")
    SetupDialog(first_run=False).exec()


def ensure_dependencies(_app: QApplication) -> None:
    """Показывает окно настройки при первом запуске или если ядро не установлено.

    Быстрый путь не импортирует markitdown и не запускает Pandoc: маркер
    пишется только после успешной установки, поэтому наличия пакетов
    достаточно. Тяжёлые проверки — внутри SetupDialog."""
    if _MARKER.exists() and _module_present("markitdown") and _module_present("pypandoc"):
        log.debug("Зависимости на месте, окно настройки пропущено")
        return
    log.info("Открытие окна настройки (первый запуск или ядро не установлено)")
    SetupDialog().exec()
