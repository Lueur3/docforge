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
from docforge.i18n import tr
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

        layout.addWidget(QLabel(tr("Extracting images from files (docx, pptx, pdf, epub and others)")))

        # Input files
        layout.addWidget(QLabel(tr("Input files:")))
        self._inputs = InputSelector(
            file_filters.images_filter(), file_filters.IMAGES_EXTS, "images"
        )
        self._inputs.changed.connect(self._on_inputs_changed)
        layout.addWidget(self._inputs)

        # Destination folder
        self._dest_label = QLabel(tr("Image folder:"))
        layout.addWidget(self._dest_label)
        row_out = QHBoxLayout()
        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText(tr("Where to save the images..."))
        btn_out = QPushButton(tr("Browse"))
        btn_out.setFixedWidth(80)
        btn_out.setToolTip(tr("Save folder (the <file>_images name is added automatically)"))
        btn_out.clicked.connect(self._browse_dest)
        row_out.addWidget(self._dest_edit)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Action button (turns into Cancel while a batch is running)
        self._extract_btn = QPushButton(tr("Extract images"))
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
            self._dest_label.setText(tr("Folder for the per-file image folders:"))
            self._dest_edit.setText(str(Path(paths[0]).parent))
        else:
            self._dest_label.setText(tr("Image folder:"))
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
        folder = QFileDialog.getExistingDirectory(self, tr("Select a save folder"), initial)
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
            self._log.append(tr("ℹ Skipped missing files: {n}").format(n=missing))
        if not inputs:
            self._log.append(tr("Select an input file."))
            return None

        target = self._dest_edit.text().strip()
        if not target:
            self._log.append(tr("Specify a folder for the images."))
            return None

        if len(inputs) == 1 and not self._batch():
            return [Job(inputs[0], target)]
        root = Path(target)
        return [Job(p, str(root / (Path(p).stem + "_images"))) for p in inputs]

    def _on_button(self) -> None:
        if self._runner is not None and self._runner.isRunning():
            self._runner.cancel()
            self._extract_btn.setEnabled(False)
            self._log.append(tr("ℹ Cancelling — waiting for the files in progress..."))
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
            self._log.append(tr("ℹ Extraction cancelled."))
            return

        self._last_result = (
            jobs[0].output_path if len(jobs) == 1 else str(Path(jobs[0].output_path).parent)
        )
        self._log.reset()
        self._log.append(
            tr("▶ Extracting from: {name}").format(name=jobs[0].name) if len(jobs) == 1
            else tr("▶ Batch extraction: {n} files").format(n=len(jobs))
        )
        self._extract_btn.setText(tr("Cancel"))

        # collect per-file counts so the summary can report how many images
        # were actually found (a file may simply contain none)
        self._counts: list[int] = []

        def extract(job: Job) -> None:
            self._counts.append(images.extract_images_only(job.input_path, job.output_path))

        self._runner = BatchRunner(
            jobs, extract, max_workers=pool_size(len(jobs), heavy=False)
        )
        self._runner.progress.connect(self._log.set_progress)
        self._runner.message.connect(self._log.append)
        self._runner.completed.connect(self._on_completed)
        self._runner.start()

    def _on_completed(self, ok: int, failed: int) -> None:
        self._extract_btn.setText(tr("Extract images"))
        self._extract_btn.setEnabled(True)
        total_images = sum(self._counts)
        if failed and ok:
            self._log.append(tr("✓ Processed: {ok}, failed: {failed}").format(ok=ok, failed=failed))
        elif failed:
            self._log.append(tr("✗ Could not process files: {failed}").format(failed=failed))
        elif not total_images:
            self._log.append(tr("ℹ No embedded images found in the file."))
        else:
            self._log.append(
                tr("✓ Images extracted: {n} → {path}")
                .format(n=total_images, path=self._last_result)
            )
        if ok and total_images and os.path.isdir(self._last_result):
            self._log.set_result(self._last_result)
