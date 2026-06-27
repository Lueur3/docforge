import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QCheckBox,
)
from PyQt6.QtCore import QThread, pyqtSignal

import file_filters
import image_extract
from ui_utils import StatusLog

log = logging.getLogger(__name__)

# Текстовые форматы, для которых автоопределение кодировки может ошибаться
# (charset-normalizer на системах с не-латинской локалью путает UTF-8 с cp125x)
_TEXT_EXTENSIONS = {".html", ".htm", ".txt", ".md", ".csv", ".json", ".xml"}


def _is_valid_utf8(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            f.read().decode("utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


def convert_to_markdown(input_path: str, output_path: str,
                        extract_images: bool = False) -> int:
    """Конвертирует файл в Markdown. Возвращает число извлечённых картинок."""
    from markitdown import MarkItDown, StreamInfo
    ext = Path(input_path).suffix.lower()
    size = os.path.getsize(input_path) if os.path.isfile(input_path) else -1
    log.info(
        "MarkItDown: вход=%s (формат=%s, размер=%d Б) → выход=%s, извлечение_картинок=%s",
        input_path, ext, size, output_path, extract_images,
    )
    kwargs = {}
    if ext in _TEXT_EXTENSIONS and _is_valid_utf8(input_path):
        kwargs["stream_info"] = StreamInfo(charset="utf-8")
        log.debug("MarkItDown: применена подсказка кодировки UTF-8")
    if extract_images:
        # иначе MarkItDown пишет обрезанный 'data:image/png;base64...'
        kwargs["keep_data_uris"] = True
    result = MarkItDown().convert(input_path, **kwargs)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)
    log.info("MarkItDown: записано %d символов в %s", len(result.text_content), output_path)
    if extract_images:
        count = image_extract.extract_to_markdown_media(output_path)
        log.info("MarkItDown: извлечено изображений: %d", count)
        return count
    return 0


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
            self.log.emit(f"✗ Ошибка MarkItDown: {e}")
            self.done.emit(False)


class MarkItDownTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: Optional[_ConvertWorker] = None
        self._build_ui()

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
        btn_out.clicked.connect(self._browse_output)
        row_out.addWidget(self._output_edit)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Извлечение картинок
        self._extract_chk = QCheckBox("Извлекать изображения в папку рядом с файлом")
        self._extract_chk.setChecked(True)
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

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл", "", file_filters.MARKITDOWN_INPUT
        )
        if not path:
            return
        self._input_edit.setText(path)
        # путь вывода всегда следует за новым входным файлом
        self._output_edit.setText(str(Path(path).with_suffix(".md")))

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

        self._convert_btn.setEnabled(False)
        self._log.append(f"▶ Конвертация: {input_path}")

        self._worker = _ConvertWorker(
            input_path, output_path, self._extract_chk.isChecked()
        )
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _success: bool) -> None:
        self._convert_btn.setEnabled(True)
