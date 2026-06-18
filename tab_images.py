import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog,
)
from PyQt6.QtCore import QThread, pyqtSignal

import file_filters
import image_extract

log = logging.getLogger(__name__)


class _ExtractWorker(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, input_path: str, dest_dir: str) -> None:
        super().__init__()
        self._input = input_path
        self._dest  = dest_dir

    def run(self) -> None:
        try:
            count = image_extract.extract_images_only(self._input, self._dest)
            if count:
                self.log.emit(f"✓ Извлечено изображений: {count} → {self._dest}")
            else:
                self.log.emit("ℹ В файле не найдено встроенных изображений.")
            self.done.emit(True)
        except Exception as e:
            log.exception("Извлечение изображений: ошибка для %s", self._input)
            self.log.emit(f"✗ Ошибка: {e}")
            self.done.emit(False)


class ImagesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: Optional[_ExtractWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel("Извлечение изображений из файла (docx, pptx, pdf, epub и др.)"))

        # Входной файл
        layout.addWidget(QLabel("Входной файл:"))
        row_in = QHBoxLayout()
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("Путь к файлу...")
        btn_in = QPushButton("Обзор")
        btn_in.setFixedWidth(80)
        btn_in.clicked.connect(self._browse_input)
        row_in.addWidget(self._input_edit)
        row_in.addWidget(btn_in)
        layout.addLayout(row_in)

        # Папка назначения
        layout.addWidget(QLabel("Папка для изображений:"))
        row_out = QHBoxLayout()
        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText("Куда сохранить картинки...")
        btn_out = QPushButton("Обзор")
        btn_out.setFixedWidth(80)
        btn_out.clicked.connect(self._browse_dest)
        row_out.addWidget(self._dest_edit)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Кнопка
        self._extract_btn = QPushButton("Извлечь изображения")
        self._extract_btn.setObjectName("btn_convert")
        self._extract_btn.setFixedHeight(36)
        self._extract_btn.clicked.connect(self._run_extract)
        layout.addWidget(self._extract_btn)

        # Лог
        layout.addWidget(QLabel("Лог:"))
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(100)
        layout.addWidget(self._log)

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл", "", file_filters.IMAGES_INPUT
        )
        if not path:
            return
        self._input_edit.setText(path)
        # путь назначения всегда следует за новым файлом: <имя>_images рядом с ним;
        # папка создаётся автоматически при извлечении — заранее создавать не нужно
        self._dest_edit.setText(str(Path(path).with_suffix("")) + "_images")

    def _browse_dest(self) -> None:
        initial = self._dest_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Выбрать папку", initial)
        if folder:
            self._dest_edit.setText(folder)

    def _run_extract(self) -> None:
        input_path = self._input_edit.text().strip()
        dest_dir   = self._dest_edit.text().strip()

        if not input_path or not dest_dir:
            self._log.append("Укажите входной файл и папку для изображений.")
            return
        if not os.path.isfile(input_path):
            self._log.append(f"Файл не найден: {input_path}")
            return

        self._extract_btn.setEnabled(False)
        self._log.append(f"▶ Извлечение из: {input_path}")

        self._worker = _ExtractWorker(input_path, dest_dir)
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _success: bool) -> None:
        self._extract_btn.setEnabled(True)
