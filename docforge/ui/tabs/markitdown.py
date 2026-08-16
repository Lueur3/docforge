import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QCheckBox,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut

from docforge import settings
from docforge.core.errors import friendly_error
from docforge.core.markitdown import convert_to_markdown
from docforge.ui import file_filters
from docforge.ui.dialogs import resolve_output_conflict
from docforge.ui.widgets import StatusLog

log = logging.getLogger(__name__)


class _ConvertWorker(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, input_path: str, output_path: str, extract_images: bool) -> None:
        super().__init__()
        self._input   = input_path
        self._output  = output_path
        self._extract = extract_images

    def run(self) -> None:
        try:
            count = convert_to_markdown(self._input, self._output, self._extract)
            if count:
                media = str(Path(self._output).with_suffix("")) + "_media"
                self.log.emit(f"ℹ Извлечено изображений: {count} → {media}")
            self.log.emit(f"✓ Готово → {self._output}")
            self.done.emit(True)
        except Exception as e:
            log.exception(
                "MarkItDown: ошибка конвертации %s → %s", self._input, self._output
            )
            self.log.emit(f"✗ Ошибка MarkItDown: {friendly_error(e)}")
            self.done.emit(False)


class MarkItDownTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: Optional[_ConvertWorker] = None
        self._last_output: str = ""
        self._build_ui()
        self.setAcceptDrops(True)
        QShortcut(QKeySequence("Ctrl+O"), self, self._browse_input)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._run_convert)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._run_convert)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Входной файл
        layout.addWidget(QLabel("Входной файл:"))
        row_in = QHBoxLayout()
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("Путь к файлу...")
        btn_in = QPushButton("Обзор")
        btn_in.setFixedWidth(80)
        btn_in.setToolTip("Выбрать файл (Ctrl+O). Можно также перетащить файл в окно.")
        btn_in.clicked.connect(self._browse_input)
        row_in.addWidget(self._input_edit)
        row_in.addWidget(btn_in)
        layout.addLayout(row_in)

        # Выходной файл
        layout.addWidget(QLabel("Выходной файл (.md):"))
        row_out = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Путь к файлу результата...")
        btn_out = QPushButton("Обзор")
        btn_out.setFixedWidth(80)
        btn_out.setToolTip("Куда сохранить .md")
        btn_out.clicked.connect(self._browse_output)
        row_out.addWidget(self._output_edit)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Извлечение картинок (состояние запоминается между запусками)
        self._extract_chk = QCheckBox("Извлекать изображения в папку рядом с файлом")
        self._extract_chk.setChecked(settings.get_bool("markitdown/extract_images", True))
        self._extract_chk.toggled.connect(
            lambda v: settings.put("markitdown/extract_images", v)
        )
        layout.addWidget(self._extract_chk)

        # Кнопка конвертации
        self._convert_btn = QPushButton("Конвертировать")
        self._convert_btn.setObjectName("btn_convert")
        self._convert_btn.setFixedHeight(36)
        self._convert_btn.clicked.connect(self._run_convert)
        layout.addWidget(self._convert_btn)

        # строка статуса + «Подробнее»
        self._log = StatusLog()
        layout.addWidget(self._log)

        # растяжка внизу прижимает содержимое вверх — без больших отступов
        layout.addStretch()

    def _set_input(self, path: str) -> None:
        self._input_edit.setText(path)
        # путь вывода всегда следует за новым входным файлом
        self._output_edit.setText(str(Path(path).with_suffix(".md")))
        settings.remember_dir(path)

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл", settings.last_dir(), file_filters.MARKITDOWN_INPUT
        )
        if path:
            self._set_input(path)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self._set_input(path)
                break

    def _browse_output(self) -> None:
        initial = self._output_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", initial, "Markdown (*.md)"
        )
        if path:
            self._output_edit.setText(path)

    def _run_convert(self) -> None:
        input_path  = self._input_edit.text().strip()
        output_path = self._output_edit.text().strip()

        if not input_path or not output_path:
            self._log.append("Укажите входной и выходной файлы.")
            return
        if not os.path.isfile(input_path):
            self._log.append(f"Файл не найден: {input_path}")
            return

        resolved = resolve_output_conflict(self, output_path, input_path)
        if resolved is None:
            self._log.append("ℹ Конвертация отменена.")
            return
        output_path = resolved
        self._output_edit.setText(output_path)

        self._convert_btn.setEnabled(False)
        self._last_output = output_path
        self._log.reset()
        self._log.append(f"▶ Конвертация: {input_path}")

        self._worker = _ConvertWorker(
            input_path, output_path, self._extract_chk.isChecked()
        )
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool) -> None:
        self._convert_btn.setEnabled(True)
        if success:
            self._log.set_result(self._last_output)
