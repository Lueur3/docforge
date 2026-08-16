import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from docforge import settings
from docforge.core.batch import BatchRunner, Job, pool_size
from docforge.core.markitdown import convert_to_markdown
from docforge.ui import file_filters
from docforge.ui.dialogs import resolve_batch_conflicts
from docforge.ui.inputs import InputSelector
from docforge.ui.widgets import StatusLog

log = logging.getLogger(__name__)


class MarkItDownTab(QWidget):
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
        self._inputs = InputSelector(
            file_filters.MARKITDOWN_INPUT, file_filters.MARKITDOWN_EXTS, "markitdown"
        )
        self._inputs.changed.connect(self._on_inputs_changed)
        layout.addWidget(self._inputs)

        # Output: a file for one input, a folder for several
        self._output_label = QLabel("Выходной файл (.md):")
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

        # Image extraction (the state is remembered between launches)
        self._extract_chk = QCheckBox("Извлекать изображения в папку рядом с файлом")
        self._extract_chk.setChecked(settings.get_bool("markitdown/extract_images", True))
        self._extract_chk.toggled.connect(
            lambda v: settings.put("markitdown/extract_images", v)
        )
        layout.addWidget(self._extract_chk)

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

    # --------------------------------------------------------------- inputs

    def _batch(self) -> bool:
        return self._inputs.count() > 1

    def _on_inputs_changed(self) -> None:
        paths = self._inputs.paths()
        if not paths:
            return
        if self._batch():
            self._output_label.setText("Папка результата:")
            self._output_btn.setToolTip("Папка, куда сложить готовые .md")
            self._output_edit.setText(str(Path(paths[0]).parent))
        else:
            self._output_label.setText("Выходной файл (.md):")
            self._output_btn.setToolTip("Куда сохранить результат")
            self._output_edit.setText(str(Path(paths[0]).with_suffix(".md")))

    def load_files(self, paths: list[str]) -> None:
        """Preselect files (used for Explorer hand-off)."""
        self._inputs.set_paths(paths)

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
        initial = self._output_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", initial, "Markdown (*.md)")
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
        return [Job(p, str(out_dir / (Path(p).stem + ".md"))) for p in inputs]

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

        self._last_result = jobs[0].output_path if len(jobs) == 1 else str(out_dir)
        self._log.reset()
        self._log.append(
            f"▶ Конвертация: {jobs[0].name}" if len(jobs) == 1
            else f"▶ Пакетная конвертация: {len(jobs)} файлов"
        )
        self._convert_btn.setText("Отмена")

        extract = self._extract_chk.isChecked()
        self._runner = BatchRunner(
            jobs,
            lambda job: convert_to_markdown(job.input_path, job.output_path, extract),
            max_workers=pool_size(len(jobs), heavy=False),
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
