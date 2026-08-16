import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QTabWidget, QWidget,
)

from docforge.ui import file_filters
from docforge.ui.integration_dialog import open_integration_dialog
from docforge.ui.setup_dialog import open_components_dialog
from docforge.ui.tabs.images import ImagesTab
from docforge.ui.tabs.markitdown import MarkItDownTab
from docforge.ui.tabs.pandoc import PandocTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, log_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("DocForge")
        # fixed size — identical on every tab and unchanged when settings are
        # toggled; the log lives in its own window, so there is no large panel
        # here, and each tab's trailing stretch pins its fields to the top
        self.setFixedSize(640, 460)

        self._tabs = QTabWidget()
        self._tabs.addTab(MarkItDownTab(), "MarkItDown")
        self._tabs.addTab(PandocTab(), "Pandoc")
        self._tabs.addTab(ImagesTab(), "Изображения")
        self._tabs.setCornerWidget(self._build_corner())

        self.setCentralWidget(self._tabs)

        if log_file is not None:
            self._log_file = Path(log_file)
            link = QLabel(f'Лог: <a href="#">{self._log_file}</a>')
            link.setStyleSheet("color: #888; font-size: 11px;")
            link.setToolTip("Открыть папку с логами")
            link.linkActivated.connect(self._open_log_dir)
            self.statusBar().addWidget(link)
        log.debug("MainWindow создан")

    def _build_corner(self) -> QWidget:
        """Corner buttons of the tab bar — always visible."""
        corner = QWidget()
        row = QHBoxLayout(corner)
        row.setContentsMargins(0, 0, 4, 0)
        row.setSpacing(4)

        components_btn = QPushButton("Компоненты")
        components_btn.setToolTip("Установить или проверить ffmpeg, MiKTeX, Chromium и ядро")
        components_btn.clicked.connect(lambda: open_components_dialog())

        integration_btn = QPushButton("Интеграция")
        integration_btn.setToolTip("Пункт в контекстном меню Проводника и ярлык «Отправить»")
        integration_btn.clicked.connect(lambda: open_integration_dialog(self))

        row.addWidget(components_btn)
        row.addWidget(integration_btn)
        return corner

    def load_files(self, paths: list[str]) -> None:
        """Preselect files handed over by Explorer, on the most fitting tab."""
        if not paths:
            return
        ext = Path(paths[0]).suffix.lower().lstrip(".")
        # Pandoc converts between formats, so it wins when it can read the file
        order = [
            (1, file_filters.PANDOC_EXTS),
            (0, file_filters.MARKITDOWN_EXTS),
            (2, file_filters.IMAGES_EXTS),
        ]
        index = next((i for i, exts in order if ext in exts), 0)
        tab = self._tabs.widget(index)
        self._tabs.setCurrentIndex(index)
        tab.load_files(paths)
        log.info("Файлы переданы на вкладку «%s»: %d", self._tabs.tabText(index), len(paths))

    def _open_log_dir(self) -> None:
        folder = str(self._log_file.parent)
        log.debug("Открытие папки логов: %s", folder)
        try:
            os.startfile(folder)  # noqa: S606 — Windows-only, path is ours, not user input
        except OSError as e:
            log.warning("Не удалось открыть папку логов: %s", e)
