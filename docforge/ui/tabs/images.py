import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from docforge import settings
from docforge.core import images
from docforge.core.batch import BatchRunner, Job, pool_size
from docforge.ui import file_filters
from docforge.ui.dialogs import resolve_batch_conflicts
from docforge.ui.inputs import InputSelector
from docforge.ui.widgets import StatusLog

log = logging.getLogger(__name__)


class ImagesTab(QWidget):
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

        layout.addWidget(QLabel("Извлечение изображений из файлов (docx, pptx, pdf, epub и др.)"))

        # Input files
        layout.addWidget(QLabel("Входные файлы:"))
        self._inputs = InputSelector(
            file_filters.IMAGES_INPUT, file_filters.IMAGES_EXTS, "images"
        )
        self._inputs.changed.connect(self._on_inputs_changed)
        layout.addWidget(self._inputs)

        # Destination folder
        self._dest_label = QLabel("Папка для изображений:")
        layout.addWidget(self._dest_label)
        row_out = QHBoxLayout()
        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText("Куда сохранить картинки...")
        btn_out = QPushButton("Обзор")
        btn_out.setFixedWidth(80)
        btn_out.setToolTip("Папка для сохранения (имя <файл>_images добавляется само)")
        btn_out.clicked.connect(self._browse_dest)
        row_out.addWidget(self._dest_edit)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Action button (turns into Cancel while a batch is running)
        self._extract_btn = QPushButton("Извлечь изображения")
        self._extract_btn.setObjectName("btn_convert")
        self._extract_btn.setFixedHeight(36)
        self._extract_btn.clicked.connect(self._on_button)
        layout.addWidget(self._extract_btn)

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
            # each file gets its own <name>_images subfolder inside this one
            self._dest_label.setText("Папка для подпапок с изображениями:")
            self._dest_edit.setText(str(Path(paths[0]).parent))
        else:
            self._dest_label.setText("Папка для изображений:")
            self._dest_edit.setText(str(Path(paths[0]).with_suffix("")) + "_images")

    def load_files(self, paths: list[str]) -> None:
        """Preselect files (used for Explorer hand-off)."""
        self._inputs.set_paths(paths)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self._inputs.accept_drop(event.mimeData().urls())

    def _browse_dest(self) -> None:
        initial = self._dest_edit.text() or settings.last_dir() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Выбрать папку для сохранения", initial)
        if not folder:
            return
        if self._batch():
            self._dest_edit.setText(folder)
            return
        # the dialog picks a parent folder — we append <file>_images ourselves,
        # otherwise the user would have to type the folder name by hand
        paths = self._inputs.paths()
        if paths:
            self._dest_edit.setText(str(Path(folder) / (Path(paths[0]).stem + "_images")))
        else:
            self._dest_edit.setText(folder)

    # ------------------------------------------------------------------ run

    def _build_jobs(self) -> list[Job] | None:
        inputs = [p for p in self._inputs.paths() if os.path.isfile(p)]
        missing = self._inputs.count() - len(inputs)
        if missing:
            self._log.append(f"ℹ Пропущено несуществующих файлов: {missing}")
        if not inputs:
            self._log.append("Укажите входной файл.")
            return None

        target = self._dest_edit.text().strip()
        if not target:
            self._log.append("Укажите папку для изображений.")
            return None

        if len(inputs) == 1 and not self._batch():
            return [Job(inputs[0], target)]
        root = Path(target)
        return [Job(p, str(root / (Path(p).stem + "_images"))) for p in inputs]

    def _on_button(self) -> None:
        if self._runner is not None and self._runner.isRunning():
            self._runner.cancel()
            self._extract_btn.setEnabled(False)
            self._log.append("ℹ Отмена — ждём завершения текущих файлов...")
            return
        self._start()

    def _start(self) -> None:
        if self._runner is not None and self._runner.isRunning():
            return
        jobs = self._build_jobs()
        if not jobs:
            return
        jobs = resolve_batch_conflicts(self, jobs, is_dir=True)
        if not jobs:
            self._log.append("ℹ Извлечение отменено.")
            return

        self._last_result = (
            jobs[0].output_path if len(jobs) == 1 else str(Path(jobs[0].output_path).parent)
        )
        self._log.reset()
        self._log.append(
            f"▶ Извлечение из: {jobs[0].name}" if len(jobs) == 1
            else f"▶ Пакетное извлечение: {len(jobs)} файлов"
        )
        self._extract_btn.setText("Отмена")

        self._runner = BatchRunner(
            jobs,
            lambda job: images.extract_images_only(job.input_path, job.output_path),
            max_workers=pool_size(len(jobs), heavy=False),
        )
        self._runner.progress.connect(self._log.set_progress)
        self._runner.message.connect(self._log.append)
        self._runner.completed.connect(self._on_completed)
        self._runner.start()

    def _on_completed(self, ok: int, failed: int) -> None:
        self._extract_btn.setText("Извлечь изображения")
        self._extract_btn.setEnabled(True)
        if failed and ok:
            self._log.append(f"✓ Обработано: {ok}, с ошибкой: {failed}")
        elif failed:
            self._log.append(f"✗ Не удалось обработать файлов: {failed}")
        else:
            self._log.append(f"✓ Готово: {ok} файлов → {self._last_result}")
        if ok and os.path.isdir(self._last_result):
            self._log.set_result(self._last_result)
