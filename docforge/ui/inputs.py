"""Input selector: one file or many, from a dialog, a folder scan or a drop."""
import os
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLineEdit, QMenu, QPushButton, QWidget,
)

from docforge import settings


def scan_folder(folder: str, exts: list[str], *, recursive: bool = False) -> list[str]:
    """Collect supported files from a folder (sorted, case-insensitive match)."""
    wanted = {f".{e.lower()}" for e in exts}
    root = Path(folder)
    it = root.rglob("*") if recursive else root.glob("*")
    return sorted(str(p) for p in it if p.is_file() and p.suffix.lower() in wanted)


def summarize(paths: list[str]) -> str:
    """Text for the input field: a full path for one file, a count for many."""
    if len(paths) == 1:
        return paths[0]
    names = ", ".join(Path(p).name for p in paths[:3])
    tail = ", ..." if len(paths) > 3 else ""
    return f"{len(paths)} файлов: {names}{tail}"


class InputSelector(QWidget):
    """Field plus "Обзор" (multi-select) and "Папка" (scan a directory)."""

    changed = pyqtSignal()

    def __init__(self, file_filter: str, exts: list[str], recent_scope: str = "") -> None:
        super().__init__()
        self._filter = file_filter
        self._exts = exts
        self._scope = recent_scope
        self._paths: list[str] = []

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Путь к файлу или несколько файлов...")
        self._edit.editingFinished.connect(self._on_text_edited)

        btn_files = QPushButton("Обзор")
        btn_files.setFixedWidth(80)
        btn_files.setToolTip(
            "Выбрать один или несколько файлов (Ctrl+O). "
            "Файлы также можно перетащить в окно."
        )
        btn_files.clicked.connect(self.browse_files)

        btn_dir = QPushButton("Папка")
        btn_dir.setFixedWidth(70)
        btn_dir.setToolTip("Взять все поддерживаемые файлы из папки")
        btn_dir.clicked.connect(self.browse_folder)

        self._recent_btn = QPushButton("▾")
        self._recent_btn.setFixedWidth(26)
        self._recent_btn.setToolTip("Недавние файлы")
        self._recent_btn.clicked.connect(self._show_recent)

        row.addWidget(self._edit)
        row.addWidget(btn_files)
        row.addWidget(btn_dir)
        row.addWidget(self._recent_btn)
        self._recent_btn.setVisible(bool(self._scope))

    # ------------------------------------------------------------------ state

    def paths(self) -> list[str]:
        return list(self._paths)

    def count(self) -> int:
        return len(self._paths)

    def set_paths(self, paths: list[str], *, remember: bool = True) -> None:
        self._paths = [p for p in paths if p]
        self._edit.setText(summarize(self._paths) if self._paths else "")
        if self._paths:
            settings.remember_dir(self._paths[0])
            if remember and self._scope:
                settings.push_recent(self._scope, self._paths)
        self.changed.emit()

    def _show_recent(self) -> None:
        """Drop-down with the last selections; missing files are marked."""
        menu = QMenu(self)
        entries = settings.get_recent(self._scope)
        if not entries:
            menu.addAction("Пока пусто").setEnabled(False)
        for entry in entries:
            label = summarize(entry)
            if len(label) > 70:
                label = "..." + label[-67:]
            if not all(os.path.exists(p) for p in entry):
                label += "  (нет на диске)"
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked, e=entry: self.set_paths(e))
        menu.exec(self._recent_btn.mapToGlobal(self._recent_btn.rect().bottomLeft()))

    def _on_text_edited(self) -> None:
        """A hand-typed path replaces the selection; the summary text is kept."""
        text = self._edit.text().strip()
        if not text:
            self._paths = []
            self.changed.emit()
            return
        if len(self._paths) > 1 and text == summarize(self._paths):
            return  # the summary of a multi-file selection, not a real path
        self._paths = [text]
        self.changed.emit()

    # ----------------------------------------------------------------- choose

    def browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выбрать файлы", settings.last_dir(), self._filter
        )
        if paths:
            self.set_paths(paths)

    def browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выбрать папку с файлами", settings.last_dir()
        )
        if not folder:
            return
        found = scan_folder(folder, self._exts)
        if found:
            self.set_paths(found)
        else:
            self._edit.setText("")
            self._paths = []
            self.changed.emit()

    def accept_drop(self, urls) -> bool:
        """Take files from a drag-and-drop; a dropped folder is scanned."""
        collected: list[str] = []
        for url in urls:
            path = url.toLocalFile()
            if not path:
                continue
            if os.path.isdir(path):
                collected += scan_folder(path, self._exts)
            elif os.path.isfile(path):
                collected.append(path)
        if not collected:
            return False
        self.set_paths(collected)
        return True
