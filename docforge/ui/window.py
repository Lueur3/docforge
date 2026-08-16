import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QTabWidget, QWidget,
)

from docforge import i18n, settings
from docforge.i18n import tr
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
        self._tabs.addTab(ImagesTab(), tr("Images"))
        self._tabs.setCornerWidget(self._build_corner())

        self.setCentralWidget(self._tabs)
        self._build_status_bar(log_file)
        log.debug("MainWindow создан")

    def _build_corner(self) -> QWidget:
        """Corner buttons of the tab bar — always visible."""
        corner = QWidget()
        row = QHBoxLayout(corner)
        row.setContentsMargins(0, 0, 4, 0)
        row.setSpacing(4)

        components_btn = QPushButton(tr("Components"))
        components_btn.setToolTip(tr("Install or check ffmpeg, MiKTeX, Chromium and the core"))
        components_btn.clicked.connect(lambda: open_components_dialog())

        integration_btn = QPushButton(tr("Integration"))
        integration_btn.setToolTip(tr("Explorer context-menu entry and a SendTo shortcut"))
        integration_btn.clicked.connect(lambda: open_integration_dialog(self))

        row.addWidget(components_btn)
        row.addWidget(integration_btn)
        return corner

    def _build_status_bar(self, log_file: Path | None) -> None:
        if log_file is not None:
            self._log_file = Path(log_file)
            link = QLabel(f'{tr("Log: ")}<a href="#">{self._log_file.name}</a>')
            link.setStyleSheet("color: #888; font-size: 11px;")
            link.setToolTip(str(self._log_file))
            link.linkActivated.connect(self._open_log_dir)
            self.statusBar().addWidget(link)

        lang_label = QLabel(tr("Interface language"))
        lang_label.setStyleSheet("color: #888; font-size: 11px;")
        self._lang_combo = QComboBox()
        for code, title in i18n.LANGUAGES.items():
            self._lang_combo.addItem(title, code)
        idx = self._lang_combo.findData(i18n.current())
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.statusBar().addPermanentWidget(lang_label)
        self.statusBar().addPermanentWidget(self._lang_combo)

    def _on_language_changed(self) -> None:
        code = self._lang_combo.currentData()
        if code == i18n.current():
            return
        settings.put("ui/language", code)
        i18n.set_language(code)
        # widgets take their text at build time, so a restart is the honest
        # way to apply it everywhere (dialogs, tab titles, tooltips)
        QMessageBox.information(
            self, tr("Language changed"),
            tr("The interface language has been changed. Restart DocForge to apply it."),
        )

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
