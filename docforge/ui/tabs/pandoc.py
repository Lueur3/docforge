import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from docforge import settings
from docforge.core import pandoc
from docforge.core.batch import BatchRunner, Job, pool_size
from docforge.core.pandoc import FORMATS, HIGHLIGHT_STYLES, PandocOptions
from docforge.ui import file_filters
from docforge.ui.dialogs import resolve_batch_conflicts
from docforge.ui.inputs import InputSelector
from docforge.ui.widgets import StatusLog

log = logging.getLogger(__name__)


class PandocTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._runner: Optional[BatchRunner] = None
        self._last_result: str = ""
        self._build_ui()
        self.setAcceptDrops(True)
        QShortcut(QKeySequence("Ctrl+O"), self, self._inputs.browse_files)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._start)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._start)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Input files
        layout.addWidget(QLabel("Входные файлы:"))
        self._inputs = InputSelector(file_filters.PANDOC_INPUT, file_filters.PANDOC_EXTS)
        self._inputs.changed.connect(self._on_inputs_changed)
        layout.addWidget(self._inputs)

        # Output format
        layout.addWidget(QLabel("Формат вывода:"))
        self._fmt_combo = QComboBox()
        for label, _writer, ext, _standalone in FORMATS:
            self._fmt_combo.addItem(f"{label}  (.{ext})", ext)
        self._fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(self._fmt_combo)

        # Output: a file for one input, a folder for several
        self._output_label = QLabel("Выходной файл:")
        layout.addWidget(self._output_label)
        row_out = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Путь к файлу результата...")
        self._output_btn = QPushButton("Обзор")
        self._output_btn.setFixedWidth(80)
        self._output_btn.setToolTip("Куда сохранить результат")
        self._output_btn.clicked.connect(self._browse_output)
        row_out.addWidget(self._output_edit)
        row_out.addWidget(self._output_btn)
        layout.addLayout(row_out)

        # Settings (collapsed by default)
        self._settings_btn = QPushButton("Настройки ▸")
        self._settings_btn.setCheckable(True)
        self._settings_btn.setFixedHeight(24)
        self._settings_btn.clicked.connect(self._toggle_settings)
        layout.addWidget(self._settings_btn)

        self._settings_box = self._build_settings_box()
        self._settings_box.hide()
        layout.addWidget(self._settings_box)

        # Convert button (turns into Cancel while a batch is running)
        self._convert_btn = QPushButton("Конвертировать")
        self._convert_btn.setObjectName("btn_convert")
        self._convert_btn.setFixedHeight(36)
        self._convert_btn.clicked.connect(self._on_button)
        layout.addWidget(self._convert_btn)

        # status line + details button
        self._log = StatusLog()
        layout.addWidget(self._log)

        # trailing stretch pins the content to the top — no large gaps
        layout.addStretch()

        # restore the last format (after the combo has been filled)
        idx = self._fmt_combo.findData(settings.get_str("pandoc/format", "md"))
        if idx >= 0:
            self._fmt_combo.setCurrentIndex(idx)
        self._update_pdf_controls()

    def _build_settings_box(self) -> QWidget:
        """Build the collapsible settings panel (Pandoc options + PDF params)."""
        box = QWidget()
        sbox = QVBoxLayout(box)
        sbox.setContentsMargins(0, 0, 0, 0)
        sbox.setSpacing(6)

        # Pandoc options
        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)
        self._toc_chk = QCheckBox("Оглавление")
        self._toc_chk.setChecked(settings.get_bool("pandoc/toc", False))
        self._toc_chk.toggled.connect(lambda v: settings.put("pandoc/toc", v))
        self._numsec_chk = QCheckBox("Нумерация разделов")
        self._numsec_chk.setChecked(settings.get_bool("pandoc/numsec", False))
        self._numsec_chk.toggled.connect(lambda v: settings.put("pandoc/numsec", v))
        opt_row.addWidget(self._toc_chk)
        opt_row.addWidget(self._numsec_chk)
        opt_row.addWidget(QLabel("Подсветка кода:"))
        self._highlight_combo = QComboBox()
        for label, _value in HIGHLIGHT_STYLES:
            self._highlight_combo.addItem(label)
        self._highlight_combo.setCurrentIndex(settings.get_int("pandoc/highlight", 0))
        self._highlight_combo.currentIndexChanged.connect(
            lambda i: settings.put("pandoc/highlight", i)
        )
        opt_row.addWidget(self._highlight_combo)
        opt_row.addStretch()
        sbox.addLayout(opt_row)

        # PDF parameters (enabled only when the output format is PDF)
        pdf_row = QHBoxLayout()
        pdf_row.setSpacing(8)
        pdf_row.addWidget(QLabel("PDF — движок:"))
        self._engine_combo = QComboBox()
        # Chromium first — the default PDF engine
        self._engine_combo.addItem("Chromium (как браузер)", "chromium")
        self._engine_combo.addItem("xelatex (LaTeX)", "latex")
        idx = self._engine_combo.findData(settings.get_str("pandoc/engine", "chromium"))
        if idx >= 0:
            self._engine_combo.setCurrentIndex(idx)
        self._engine_combo.currentIndexChanged.connect(
            lambda: settings.put("pandoc/engine", self._engine_combo.currentData())
        )
        pdf_row.addWidget(self._engine_combo)
        pdf_row.addWidget(QLabel("поля:"))
        self._margin_edit = QLineEdit(settings.get_str("pandoc/margin", "2cm"))
        self._margin_edit.setFixedWidth(70)
        self._margin_edit.setToolTip(
            "Например: 2cm, 1.5cm, 1in, 20mm. Пусто — поля движка по умолчанию."
        )
        self._margin_edit.editingFinished.connect(
            lambda: settings.put("pandoc/margin", self._margin_edit.text().strip())
        )
        pdf_row.addWidget(self._margin_edit)
        pdf_row.addStretch()
        sbox.addLayout(pdf_row)
        return box

    def _toggle_settings(self, checked: bool) -> None:
        self._settings_box.setVisible(checked)
        self._settings_btn.setText("Настройки ▾" if checked else "Настройки ▸")

    def _update_pdf_controls(self) -> None:
        """Engine and margins are only enabled for the PDF format."""
        is_pdf = self._current_ext() == "pdf"
        self._engine_combo.setEnabled(is_pdf)
        self._margin_edit.setEnabled(is_pdf)

    # --------------------------------------------------------------- state

    def _current_ext(self) -> str:
        return self._fmt_combo.currentData()

    def _current_writer(self) -> str:
        return FORMATS[self._fmt_combo.currentIndex()][1]

    def _current_standalone(self) -> bool:
        return FORMATS[self._fmt_combo.currentIndex()][3]

    def _batch(self) -> bool:
        return self._inputs.count() > 1

    def _options(self) -> PandocOptions:
        return PandocOptions(
            writer=self._current_writer(),
            standalone=self._current_standalone(),
            toc=self._toc_chk.isChecked(),
            number_sections=self._numsec_chk.isChecked(),
            highlight=HIGHLIGHT_STYLES[self._highlight_combo.currentIndex()][1],
            pdf_engine=self._engine_combo.currentData(),
            margin=self._margin_edit.text().strip(),
        )

    # --------------------------------------------------------------- inputs

    def _on_inputs_changed(self) -> None:
        paths = self._inputs.paths()
        if not paths:
            return
        if self._batch():
            self._output_label.setText("Папка результата:")
            self._output_btn.setToolTip("Папка, куда сложить готовые файлы")
            self._output_edit.setText(str(Path(paths[0]).parent))
        else:
            self._output_label.setText("Выходной файл:")
            self._output_btn.setToolTip("Куда сохранить результат")
            self._output_edit.setText(str(Path(paths[0]).with_suffix(f".{self._current_ext()}")))

    def _on_format_changed(self) -> None:
        current = self._output_edit.text()
        if current and not self._batch():
            self._output_edit.setText(str(Path(current).with_suffix(f".{self._current_ext()}")))
        settings.put("pandoc/format", self._current_ext())
        self._update_pdf_controls()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self._inputs.accept_drop(event.mimeData().urls())

    def _browse_output(self) -> None:
        if self._batch():
            folder = QFileDialog.getExistingDirectory(
                self, "Папка для результатов", self._output_edit.text() or settings.last_dir()
            )
            if folder:
                self._output_edit.setText(folder)
            return
        ext = self._current_ext()
        initial = self._output_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", initial, f"{ext.upper()} (*.{ext})"
        )
        if path:
            self._output_edit.setText(path)

    # ------------------------------------------------------------------ run

    def _build_jobs(self) -> list[Job] | None:
        inputs = [p for p in self._inputs.paths() if os.path.isfile(p)]
        missing = self._inputs.count() - len(inputs)
        if missing:
            self._log.append(f"ℹ Пропущено несуществующих файлов: {missing}")
        if not inputs:
            self._log.append("Укажите входной файл.")
            return None

        target = self._output_edit.text().strip()
        if not target:
            self._log.append("Укажите, куда сохранить результат.")
            return None

        if len(inputs) == 1 and not self._batch():
            return [Job(inputs[0], target)]
        out_dir = Path(target)
        ext = self._current_ext()
        return [Job(p, str(out_dir / f"{Path(p).stem}.{ext}")) for p in inputs]

    def _on_button(self) -> None:
        if self._runner is not None and self._runner.isRunning():
            self._runner.cancel()
            self._convert_btn.setEnabled(False)
            self._log.append("ℹ Отмена — ждём завершения текущих файлов...")
            return
        self._start()

    def _start(self) -> None:
        if self._runner is not None and self._runner.isRunning():
            return
        jobs = self._build_jobs()
        if not jobs:
            return
        jobs = resolve_batch_conflicts(self, jobs)
        if not jobs:
            self._log.append("ℹ Конвертация отменена.")
            return

        out_dir = Path(jobs[0].output_path).parent
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._log.append(f"✗ Не удалось создать папку результата: {e}")
            return

        opts = self._options()
        self._last_result = jobs[0].output_path if len(jobs) == 1 else str(out_dir)
        self._log.reset()
        self._log.append(
            f"▶ Конвертация в .{self._current_ext()}: {jobs[0].name}" if len(jobs) == 1
            else f"▶ Пакетная конвертация в .{self._current_ext()}: {len(jobs)} файлов"
        )
        self._convert_btn.setText("Отмена")

        # one message channel for all jobs — engine notes go to the details log
        say = self._log.append if len(jobs) == 1 else (lambda _m: None)
        self._runner = BatchRunner(
            jobs,
            lambda job: pandoc.convert(job.input_path, job.output_path, opts, say),
            max_workers=pool_size(len(jobs), heavy=opts.is_heavy),
        )
        self._runner.progress.connect(self._log.set_progress)
        self._runner.message.connect(self._log.append)
        self._runner.completed.connect(self._on_completed)
        self._runner.start()

    def _on_completed(self, ok: int, failed: int) -> None:
        self._convert_btn.setText("Конвертировать")
        self._convert_btn.setEnabled(True)
        if failed and ok:
            self._log.append(f"✓ Готово: {ok}, с ошибкой: {failed}")
        elif failed:
            self._log.append(f"✗ Не удалось конвертировать файлов: {failed}")
        elif ok == 1:
            self._log.append(f"✓ Готово → {self._last_result}")
        else:
            self._log.append(f"✓ Готово: {ok} файлов → {self._last_result}")
        if ok:
            self._log.set_result(self._last_result)
