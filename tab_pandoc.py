import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QComboBox,
)
from PyQt6.QtCore import QThread, pyqtSignal


# Форматы: (отображаемое имя, расширение, флаг --standalone)
FORMATS: list[tuple[str, str, bool]] = [
    ("Markdown",         "md",   False),
    ("HTML",             "html", True),
    ("Word Document",    "docx", False),
    ("EPUB",             "epub", True),
    ("reStructuredText", "rst",  False),
    ("Plain Text",       "txt",  False),
    ("LaTeX",            "tex",  True),
    ("ODT",              "odt",  False),
    ("RTF",              "rtf",  False),
    ("PDF",              "pdf",  False),
]

# Текстовые форматы — добавляем --output-encoding=utf-8
_TEXT_FORMATS = {"md", "html", "rst", "txt", "tex", "rtf"}


class _ConvertWorker(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, input_path: str, output_path: str, fmt: str, standalone: bool) -> None:
        super().__init__()
        self._input      = input_path
        self._output     = output_path
        self._fmt        = fmt
        self._standalone = standalone

    def run(self) -> None:
        try:
            import pypandoc

            extra: list[str] = []
            if self._standalone:
                extra.append("--standalone")
            if self._fmt in _TEXT_FORMATS:
                extra.append("--output-encoding=utf-8")

            pypandoc.convert_file(
                self._input,
                self._fmt,
                outputfile=self._output,
                extra_args=extra,
                encoding="utf-8",
            )
            self.log.emit(f"✓ Готово → {self._output}")
            self.done.emit(True)
        except Exception as e:
            error_msg = str(e)
            # --output-encoding не поддерживается старым Pandoc — повторяем без него
            if "--output-encoding" in error_msg and "--output-encoding=utf-8" in extra:
                try:
                    extra.remove("--output-encoding=utf-8")
                    pypandoc.convert_file(
                        self._input,
                        self._fmt,
                        outputfile=self._output,
                        extra_args=extra,
                        encoding="utf-8",
                    )
                    self.log.emit(f"✓ Готово → {self._output}")
                    self.done.emit(True)
                    return
                except Exception as e2:
                    error_msg = str(e2)
            self.log.emit(f"✗ Ошибка: {error_msg}")
            self.done.emit(False)


class PandocTab(QWidget):
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

        # Формат вывода
        layout.addWidget(QLabel("Формат вывода:"))
        self._fmt_combo = QComboBox()
        for label, ext, _ in FORMATS:
            self._fmt_combo.addItem(f"{label}  (.{ext})", ext)
        self._fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(self._fmt_combo)

        # Выходной файл
        layout.addWidget(QLabel("Выходной файл:"))
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

        # Лог
        layout.addWidget(QLabel("Лог:"))
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(80)
        layout.addWidget(self._log)

    def _current_ext(self) -> str:
        return self._fmt_combo.currentData()

    def _current_standalone(self) -> bool:
        idx = self._fmt_combo.currentIndex()
        return FORMATS[idx][2]

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл")
        if not path:
            return
        self._input_edit.setText(path)
        if not self._output_edit.text():
            ext = self._current_ext()
            out = Path(path).with_suffix(f".{ext}")
            self._output_edit.setText(str(out))

    def _browse_output(self) -> None:
        ext = self._current_ext()
        initial = self._output_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", initial, f"{ext.upper()} (*.{ext})"
        )
        if path:
            self._output_edit.setText(path)

    def _on_format_changed(self) -> None:
        current = self._output_edit.text()
        if current:
            self._output_edit.setText(
                str(Path(current).with_suffix(f".{self._current_ext()}"))
            )

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
        fmt = self._current_ext()
        self._log.append(f"▶ Конвертация в .{fmt}: {input_path}")

        self._worker = _ConvertWorker(
            input_path, output_path, fmt, self._current_standalone()
        )
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _success: bool) -> None:
        self._convert_btn.setEnabled(True)
