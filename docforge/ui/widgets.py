import logging
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QDialog, QSizePolicy,
)

from docforge.i18n import tr

log = logging.getLogger(__name__)


def open_in_explorer(path: str) -> None:
    """Open Explorer: a file gets selected, a folder is opened as-is."""
    p = Path(path)
    try:
        if p.is_file():
            # highlight the file in Explorer
            subprocess.run(["explorer", "/select,", str(p)])
        elif p.is_dir():
            os.startfile(str(p))  # noqa: S606 — Windows, path comes from our own result
        else:
            os.startfile(str(p.parent))  # noqa: S606
    except OSError as e:
        log.warning("Не удалось открыть проводник для %s: %s", path, e)


class StatusLog(QWidget):
    """One-line status plus a result-folder button and a details button.

    Only the latest line (✓/✗/ℹ) is visible in the window. The full log opens
    in a separate window; the folder button leads to the last result.
    """

    def __init__(self) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._status = QLabel("")
        self._status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._status.setStyleSheet("color: #888; font-size: 11px;")

        self._folder_btn = QPushButton(tr("Folder"))
        self._folder_btn.setFixedWidth(70)
        self._folder_btn.setToolTip(tr("Open the result folder"))
        self._folder_btn.clicked.connect(self._open_result)
        self._folder_btn.hide()

        self._btn = QPushButton(tr("Details"))
        self._btn.setFixedWidth(90)
        self._btn.setToolTip(tr("Open the full conversion log"))
        self._btn.clicked.connect(self._show_details)

        row.addWidget(self._status, 1)
        row.addWidget(self._folder_btn)
        row.addWidget(self._btn)

        self._lines: list[str] = []
        self._result: str | None = None
        self._dialog: QDialog | None = None
        self._view: QTextEdit | None = None

    def append(self, text: str) -> None:
        self._lines.append(text)
        self._status.setText(text)
        if "✗" in text:
            self._status.setStyleSheet("color: #e06c6c; font-size: 11px;")
        elif "✓" in text:
            self._status.setStyleSheet("color: #5cb85c; font-size: 11px;")
        else:
            self._status.setStyleSheet("color: #aaa; font-size: 11px;")
        if self._view is not None:
            self._view.append(text)

    def set_progress(self, done: int, total: int, name: str) -> None:
        """Show batch progress in the status line without growing the log."""
        self._status.setStyleSheet("color: #aaa; font-size: 11px;")
        self._status.setText(tr("▶ {done} of {total}: {name}").format(done=done, total=total, name=name))

    def reset(self) -> None:
        """Reset before a new run: hide the result-folder button."""
        self._result = None
        self._folder_btn.hide()

    def set_result(self, path: str) -> None:
        """Show the result-folder button pointing at the result."""
        self._result = path
        self._folder_btn.show()

    def _open_result(self) -> None:
        if self._result:
            open_in_explorer(self._result)

    def _show_details(self) -> None:
        if self._dialog is None:
            self._dialog = QDialog(self)
            self._dialog.setWindowTitle(tr("DocForge — conversion log"))
            self._dialog.resize(560, 360)
            lay = QVBoxLayout(self._dialog)
            self._view = QTextEdit()
            self._view.setReadOnly(True)
            lay.addWidget(self._view)
        self._view.setPlainText("\n".join(self._lines))
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
