import logging
import sys

from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QLabel,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)

from docforge.core import chromium, ffmpeg, latex
from docforge.core.installer import (
    SetupWorker, mark_setup_done, markitdown_installed, pandoc_installed, core_ready,
)

log = logging.getLogger(__name__)


class SetupDialog(QDialog):
    def __init__(self, first_run: bool = True) -> None:
        super().__init__()
        self._first_run = first_run
        self.setWindowTitle(
            "DocForge — настройка компонентов" if first_run else "DocForge — компоненты"
        )
        self.setMinimumWidth(540)

        core_ok     = markitdown_installed() and pandoc_installed()
        ffmpeg_ok   = ffmpeg.find_ffmpeg() is not None
        miktex_ok   = latex.find_pdf_engine() is not None
        chromium_ok = chromium.available()

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
        self._chk_chromium = self._add_row(
            layout,
            "Chromium — PDF «как браузер» во вкладке Pandoc",
            "pypi.org/project/playwright + браузер Chromium (~150 МБ)",
            installed=chromium_ok, required=False,
        )

        layout.addSpacing(8)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.hide()
        layout.addWidget(self._bar)

        nothing_to_install = core_ok and ffmpeg_ok and miktex_ok and chromium_ok
        if nothing_to_install:
            self._btn = QPushButton("Продолжить" if first_run else "Закрыть")
        else:
            self._btn = QPushButton("Установить и продолжить" if first_run else "Установить")
        self._btn.setFixedHeight(34)
        self._btn.clicked.connect(self._start)
        layout.addWidget(self._btn)

        self._worker: SetupWorker | None = None

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
        core     = not self._chk_core.property("installed")
        ffmpeg_  = self._chk_ffmpeg.isChecked() and not self._chk_ffmpeg.property("installed")
        miktex   = self._chk_miktex.isChecked() and not self._chk_miktex.property("installed")
        chromium_ = self._chk_chromium.isChecked() and not self._chk_chromium.property("installed")

        if not (core or ffmpeg_ or miktex or chromium_):
            self._finish()
            return

        for chk in (self._chk_core, self._chk_ffmpeg, self._chk_miktex, self._chk_chromium):
            chk.setEnabled(False)
        self._btn.setEnabled(False)
        self._bar.show()

        self._worker = SetupWorker(core, ffmpeg_, miktex, chromium_)
        self._worker.status.connect(self._status.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool, error: str) -> None:
        if not success:
            QMessageBox.warning(self, "Ошибка установки", error)
            # критично выйти только если на первом запуске не встало ядро
            if self._first_run and not (markitdown_installed() and pandoc_installed()):
                sys.exit(1)
            self._btn.setEnabled(True)
            return
        # ffmpeg мог только что установиться — подключаем его к pydub сразу
        path = ffmpeg.find_ffmpeg()
        if path:
            ffmpeg.configure_pydub(path)
        self._finish()

    def _finish(self) -> None:
        mark_setup_done()
        self.accept()


def open_components_dialog() -> None:
    """Открывает диалог компонентов в режиме управления (не первый запуск)."""
    log.info("Открытие диалога компонентов")
    SetupDialog(first_run=False).exec()


def ensure_dependencies(_app: QApplication) -> None:
    """Показывает окно настройки при первом запуске или если ядро не установлено.

    Быстрый путь не импортирует markitdown и не запускает Pandoc — маркер
    пишется только после успешной установки, поэтому наличия пакетов
    достаточно. Тяжёлые проверки — внутри SetupDialog."""
    if core_ready():
        log.debug("Зависимости на месте, окно настройки пропущено")
        return
    log.info("Открытие окна настройки (первый запуск или ядро не установлено)")
    SetupDialog().exec()
