import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel

from tab_markitdown import MarkItDownTab
from tab_pandoc import PandocTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, log_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("DocForge")
        self.setMinimumSize(600, 400)
        self.resize(600, 400)

        tabs = QTabWidget()
        tabs.addTab(MarkItDownTab(), "MarkItDown")
        tabs.addTab(PandocTab(), "Pandoc")
        self.setCentralWidget(tabs)

        if log_file is not None:
            self._log_file = Path(log_file)
            link = QLabel(f'Лог: <a href="#">{self._log_file}</a>')
            link.setStyleSheet("color: #888; font-size: 11px;")
            link.setToolTip("Открыть папку с логами")
            link.linkActivated.connect(self._open_log_dir)
            self.statusBar().addWidget(link)
        log.debug("MainWindow создан")

    def _open_log_dir(self) -> None:
        folder = str(self._log_file.parent)
        log.debug("Открытие папки логов: %s", folder)
        try:
            os.startfile(folder)  # noqa: S606 — Windows-only, путь не от пользователя
        except OSError as e:
            log.warning("Не удалось открыть папку логов: %s", e)
