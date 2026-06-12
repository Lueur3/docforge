import os
import urllib.parse
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QComboBox,
)
from PyQt6.QtCore import QThread, pyqtSignal

import pdf_helper


# Форматы: (отображаемое имя, writer для pandoc, расширение, флаг --standalone)
# Pandoc всегда читает и пишет UTF-8 — отдельные флаги кодировки не нужны.
FORMATS: list[tuple[str, str, str, bool]] = [
    ("Markdown",         "markdown", "md",   False),
    ("HTML",             "html",     "html", True),
    ("Word Document",    "docx",     "docx", False),
    ("EPUB",             "epub",     "epub", True),
    ("reStructuredText", "rst",      "rst",  False),
    ("Plain Text",       "plain",    "txt",  False),
    ("LaTeX",            "latex",    "tex",  True),
    ("ODT",              "odt",      "odt",  False),
    ("RTF",              "rtf",      "rtf",  True),
    ("PDF",              "pdf",      "pdf",  False),
]


class _ConvertWorker(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, input_path: str, output_path: str, writer: str, standalone: bool) -> None:
        super().__init__()
        self._input      = input_path
        self._output     = output_path
        self._writer     = writer
        self._standalone = standalone

    def run(self) -> None:
        try:
            import pypandoc

            extra = ["--standalone"] if self._standalone else []

            if self._writer == "pdf":
                engine = pdf_helper.find_pdf_engine()
                if engine is None:
                    self.log.emit("✗ Для вывода в PDF нужен LaTeX-движок.")
                    self.log.emit(
                        "ℹ Установите MiKTeX (https://miktex.org) — "
                        "приложение найдёт его автоматически."
                    )
                    self.done.emit(False)
                    return
                self.log.emit(f"▶ PDF-движок: {engine}")
                pdf_helper.ensure_autoinstall(engine)
                extra.append(f"--pdf-engine={engine}")
                if pdf_helper.is_unicode_engine(engine):
                    # системный шрифт с поддержкой кириллицы
                    extra += ["-V", "mainfont=Segoe UI"]
            elif self._writer == "html":
                # картинки из docx/odt/epub встраиваются прямо в html
                extra.append("--embed-resources")
            media_dir: Optional[str] = None
            if self._writer in ("markdown", "rst", "latex"):
                # картинки извлекаются в папку рядом с выходным файлом
                media_dir = str(Path(self._output).with_suffix("")) + "_media"
                extra.append(f"--extract-media={media_dir}")

            writer = self._writer
            if writer == "markdown":
                # без pandoc-атрибутов {width=...} и без raw-HTML <img> —
                # иначе картинки не рендерятся в VS Code, GitHub, Obsidian
                writer = "markdown-link_attributes-raw_html"

            pypandoc.convert_file(
                self._input,
                writer,
                outputfile=self._output,
                extra_args=extra,
            )

            if media_dir and os.path.isdir(media_dir):
                self._relativize_media_paths(media_dir)
                self.log.emit(f"ℹ Картинки извлечены в: {media_dir}")

            self.log.emit(f"✓ Готово → {self._output}")
            self.done.emit(True)
        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ Ошибка: {error_msg}")
            if self._writer == "pdf" and "package" in error_msg.lower():
                self.log.emit(
                    "ℹ Похоже, MiKTeX не хватает LaTeX-пакетов. Откройте MiKTeX Console → "
                    "Settings → установите 'Always install missing packages on-the-fly' "
                    "и повторите попытку."
                )
            self.done.emit(False)

    def _relativize_media_paths(self, media_dir: str) -> None:
        """Заменяет абсолютные пути к картинкам на относительные.

        Pandoc записывает в --extract-media абсолютный путь как есть,
        из-за чего ссылки не работают при переносе файла и не рендерятся
        в большинстве просмотрщиков.
        """
        out = Path(self._output)
        try:
            text = out.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        rel = os.path.basename(media_dir)
        fwd = media_dir.replace("\\", "/")
        variants = {media_dir, fwd, urllib.parse.quote(fwd, safe=":/")}
        new_text = text
        for v in variants:
            new_text = new_text.replace(v, rel)
        if new_text != text:
            out.write_text(new_text, encoding="utf-8")


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
        for label, _writer, ext, _standalone in FORMATS:
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

    def _current_writer(self) -> str:
        return FORMATS[self._fmt_combo.currentIndex()][1]

    def _current_standalone(self) -> bool:
        return FORMATS[self._fmt_combo.currentIndex()][3]

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл")
        if not path:
            return
        self._input_edit.setText(path)
        # путь вывода всегда следует за новым входным файлом
        self._output_edit.setText(str(Path(path).with_suffix(f".{self._current_ext()}")))

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
        self._log.append(f"▶ Конвертация в .{self._current_ext()}: {input_path}")

        self._worker = _ConvertWorker(
            input_path, output_path, self._current_writer(), self._current_standalone()
        )
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _success: bool) -> None:
        self._convert_btn.setEnabled(True)
