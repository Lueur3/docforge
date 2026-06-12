import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog,
)
from PyQt6.QtCore import QThread, pyqtSignal

import ffmpeg_helper


class _ConvertWorker(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__()
        self._input  = input_path
        self._output = output_path

    def run(self) -> None:
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(self._input)
            with open(self._output, "w", encoding="utf-8") as f:
                f.write(result.text_content)
            self.log.emit(f"✓ Готово → {self._output}")
            self.done.emit(True)
        except Exception as e:
            self.log.emit(f"✗ Ошибка: {e}")
            self.done.emit(False)


class MarkItDownTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: Optional[_ConvertWorker] = None
        self._ffmpeg_worker: Optional[ffmpeg_helper.FfmpegInstallWorker] = None
        self._build_ui()
        self._refresh_ffmpeg_status()

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

        # Кнопка конвертации
        self._convert_btn = QPushButton("Конвертировать")
        self._convert_btn.setObjectName("btn_convert")
        self._convert_btn.setFixedHeight(36)
        self._convert_btn.clicked.connect(self._run_convert)
        layout.addWidget(self._convert_btn)

        # Статус ffmpeg
        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.setSpacing(8)
        self._ffmpeg_label = QLabel()
        self._ffmpeg_install_btn = QPushButton("Установить ffmpeg")
        self._ffmpeg_install_btn.setFixedWidth(150)
        self._ffmpeg_install_btn.clicked.connect(self._install_ffmpeg)
        ffmpeg_row.addWidget(self._ffmpeg_label)
        ffmpeg_row.addWidget(self._ffmpeg_install_btn)
        ffmpeg_row.addStretch()
        layout.addLayout(ffmpeg_row)

        # Лог
        layout.addWidget(QLabel("Лог:"))
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(100)
        layout.addWidget(self._log)

    # ------------------------------------------------------------------

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл")
        if not path:
            return
        self._input_edit.setText(path)
        if not self._output_edit.text():
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

        self._worker = _ConvertWorker(input_path, output_path)
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _success: bool) -> None:
        self._convert_btn.setEnabled(True)

    # ------------------------------------------------------------------

    def _refresh_ffmpeg_status(self) -> None:
        path = ffmpeg_helper.find_ffmpeg()
        if path:
            ffmpeg_helper.configure_pydub(path)
            self._ffmpeg_label.setText("ffmpeg: ✓  доступен  (аудио/видео поддерживаются)")
            self._ffmpeg_label.setStyleSheet("color: #5cb85c; font-size: 11px;")
            self._ffmpeg_install_btn.setVisible(False)
        else:
            self._ffmpeg_label.setText("ffmpeg: не найден  (аудио/видео недоступны)")
            self._ffmpeg_label.setStyleSheet("color: #c8a050; font-size: 11px;")
            self._ffmpeg_install_btn.setVisible(True)
            self._ffmpeg_install_btn.setEnabled(True)
            self._ffmpeg_install_btn.setText("Установить ffmpeg")

    def _install_ffmpeg(self) -> None:
        self._ffmpeg_install_btn.setEnabled(False)
        self._ffmpeg_install_btn.setText("Установка...")
        self._log.append("▶ Установка ffmpeg...")

        self._ffmpeg_worker = ffmpeg_helper.FfmpegInstallWorker()
        self._ffmpeg_worker.done.connect(self._on_ffmpeg_installed)
        self._ffmpeg_worker.start()

    def _on_ffmpeg_installed(self, success: bool, path_or_error: str) -> None:
        if success:
            self._log.append(f"✓ ffmpeg установлен: {path_or_error}")
            self._ffmpeg_label.setText("ffmpeg: ✓  доступен  (аудио/видео поддерживаются)")
            self._ffmpeg_label.setStyleSheet("color: #5cb85c; font-size: 11px;")
            self._ffmpeg_install_btn.setVisible(False)
            ffmpeg_helper.configure_pydub(path_or_error)
        else:
            self._log.append(f"✗ Ошибка установки ffmpeg: {path_or_error}")
            self._ffmpeg_install_btn.setEnabled(True)
            self._ffmpeg_install_btn.setText("Установить ffmpeg")
