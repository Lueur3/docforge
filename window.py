import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel, QPushButton

import deps
from tab_markitdown import MarkItDownTab
from tab_pandoc import PandocTab
from tab_images import ImagesTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, log_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("DocForge")
        # ширина фиксирована (одинаково на всех вкладках), высота подстраивается
        # под содержимое — без больших пустот при скрытом логе/настройках
        self.setFixedWidth(640)

        tabs = QTabWidget()
        tabs.addTab(MarkItDownTab(), "MarkItDown")
        tabs.addTab(PandocTab(), "Pandoc")
        tabs.addTab(ImagesTab(), "Изображения")
        tabs.currentChanged.connect(lambda *_: self.adjustSize())

        # кнопка управления компонентами — всегда видна в углу таб-бара
        components_btn = QPushButton("Компоненты")
        components_btn.setToolTip("Установить или проверить ffmpeg, MiKTeX и ядро")
        components_btn.clicked.connect(self._open_components)
        tabs.setCornerWidget(components_btn)

        self.setCentralWidget(tabs)

        if log_file is not None:
            self._log_file = Path(log_file)
            link = QLabel(f'Лог: <a href="#">{self._log_file}</a>')
            link.setStyleSheet("color: #888; font-size: 11px;")
            link.setToolTip("Открыть папку с логами")
            link.linkActivated.connect(self._open_log_dir)
            self.statusBar().addWidget(link)
        self.adjustSize()
        log.debug("MainWindow создан")

    def _open_components(self) -> None:
        deps.open_components_dialog()

    def _open_log_dir(self) -> None:
        folder = str(self._log_file.parent)
        log.debug("Открытие папки логов: %s", folder)
        try:
            os.startfile(folder)  # noqa: S606 — Windows-only, путь не от пользователя
        except OSError as e:
            log.warning("Не удалось открыть папку логов: %s", e)
