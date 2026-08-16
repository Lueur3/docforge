import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from docforge import settings
from docforge.core import pandoc, presets
from docforge.core.batch import BatchRunner, Job, pool_size
from docforge.core.pandoc import FORMATS, HIGHLIGHT_STYLES, PandocOptions
from docforge.ui import file_filters
from docforge.ui.dialogs import resolve_batch_conflicts
from docforge.ui.inputs import InputSelector
from docforge.i18n import tr
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
        layout.addWidget(QLabel(tr("Input files:")))
        self._inputs = InputSelector(
            file_filters.pandoc_filter(), file_filters.PANDOC_EXTS, "pandoc"
        )
        self._inputs.changed.connect(self._on_inputs_changed)
        layout.addWidget(self._inputs)

        # Output format
        layout.addWidget(QLabel(tr("Output format:")))
        self._fmt_combo = QComboBox()
        for label, _writer, ext, _standalone in FORMATS:
            self._fmt_combo.addItem(f"{tr(label)}  (.{ext})", ext)
        self._fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(self._fmt_combo)

        # Output: a file for one input, a folder for several
        self._output_label = QLabel(tr("Output file:"))
        layout.addWidget(self._output_label)
        row_out = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText(tr("Path to the result file..."))
        self._output_btn = QPushButton(tr("Browse"))
        self._output_btn.setFixedWidth(80)
        self._output_btn.setToolTip(tr("Where to save the result"))
        self._output_btn.clicked.connect(self._browse_output)
        row_out.addWidget(self._output_edit)
        row_out.addWidget(self._output_btn)
        layout.addLayout(row_out)

        # Settings (collapsed by default)
        self._settings_btn = QPushButton(tr("Settings ▸"))
        self._settings_btn.setCheckable(True)
        self._settings_btn.setFixedHeight(24)
        self._settings_btn.clicked.connect(self._toggle_settings)
        layout.addWidget(self._settings_btn)

        self._settings_box = self._build_settings_box()
        self._settings_box.hide()
        layout.addWidget(self._settings_box)

        # Convert button (turns into Cancel while a batch is running)
        self._convert_btn = QPushButton(tr("Convert"))
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

        # Presets: named sets of the settings below
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_row.addWidget(QLabel(tr("Preset:")))
        self._preset_combo = QComboBox()
        self._preset_combo.setToolTip(tr("A ready-made set of settings — applied on selection"))
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self._preset_combo, 1)
        save_btn = QPushButton(tr("Save"))
        save_btn.setFixedWidth(90)
        save_btn.setToolTip(tr("Save the current settings as a preset"))
        save_btn.clicked.connect(self._save_preset)
        del_btn = QPushButton(tr("Delete"))
        del_btn.setFixedWidth(80)
        del_btn.setToolTip(tr("Delete the selected preset (built-in ones cannot be removed)"))
        del_btn.clicked.connect(self._delete_preset)
        preset_row.addWidget(save_btn)
        preset_row.addWidget(del_btn)
        sbox.addLayout(preset_row)

        # Pandoc options
        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)
        self._toc_chk = QCheckBox(tr("Table of contents"))
        self._toc_chk.setChecked(settings.get_bool("pandoc/toc", False))
        self._toc_chk.toggled.connect(lambda v: settings.put("pandoc/toc", v))
        self._numsec_chk = QCheckBox(tr("Number sections"))
        self._numsec_chk.setChecked(settings.get_bool("pandoc/numsec", False))
        self._numsec_chk.toggled.connect(lambda v: settings.put("pandoc/numsec", v))
        opt_row.addWidget(self._toc_chk)
        opt_row.addWidget(self._numsec_chk)
        opt_row.addWidget(QLabel(tr("Code highlighting:")))
        self._highlight_combo = QComboBox()
        for label, _value in HIGHLIGHT_STYLES:
            self._highlight_combo.addItem(tr(label))
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
        pdf_row.addWidget(QLabel(tr("PDF — engine:")))
        self._engine_combo = QComboBox()
        # Chromium first — the default PDF engine
        self._engine_combo.addItem(tr("Chromium (browser-style)"), "chromium")
        self._engine_combo.addItem(tr("xelatex (LaTeX)"), "latex")
        idx = self._engine_combo.findData(settings.get_str("pandoc/engine", "chromium"))
        if idx >= 0:
            self._engine_combo.setCurrentIndex(idx)
        self._engine_combo.currentIndexChanged.connect(
            lambda: settings.put("pandoc/engine", self._engine_combo.currentData())
        )
        pdf_row.addWidget(self._engine_combo)
        pdf_row.addWidget(QLabel(tr("margins:")))
        self._margin_edit = QLineEdit(settings.get_str("pandoc/margin", "2cm"))
        self._margin_edit.setFixedWidth(70)
        self._margin_edit.setToolTip(
            tr("For example: 2cm, 1.5cm, 1in, 20mm. Empty — the engine's own margins.")
        )
        self._margin_edit.editingFinished.connect(
            lambda: settings.put("pandoc/margin", self._margin_edit.text().strip())
        )
        pdf_row.addWidget(self._margin_edit)
        pdf_row.addStretch()
        sbox.addLayout(pdf_row)

        self._reload_presets()
        return box

    # -------------------------------------------------------------- presets

    def _reload_presets(self, select: str = "") -> None:
        """Refill the preset list; `select` picks an entry afterwards."""
        self._applying_preset = True
        self._preset_combo.clear()
        self._preset_combo.addItem(tr("— none —"), "")
        for name in presets.all_presets():
            self._preset_combo.addItem(tr(name), name)
        if select:
            idx = self._preset_combo.findData(select)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
        self._applying_preset = False

    def _on_preset_selected(self) -> None:
        if getattr(self, "_applying_preset", False):
            return
        name = self._preset_combo.currentData()
        if not name:
            return
        preset = presets.all_presets().get(name)
        if preset is None:
            return
        log.info("Применяется пресет: %s", name)

        idx = self._fmt_combo.findData(preset.format)
        if idx >= 0:
            self._fmt_combo.setCurrentIndex(idx)
        self._toc_chk.setChecked(preset.toc)
        self._numsec_chk.setChecked(preset.number_sections)
        h_idx = next(
            (i for i, (_label, value) in enumerate(HIGHLIGHT_STYLES) if value == preset.highlight),
            0,
        )
        self._highlight_combo.setCurrentIndex(h_idx)
        e_idx = self._engine_combo.findData(preset.engine)
        if e_idx >= 0:
            self._engine_combo.setCurrentIndex(e_idx)
        self._margin_edit.setText(preset.margin)
        settings.put("pandoc/margin", preset.margin)

    def _current_preset(self) -> presets.Preset:
        return presets.Preset(
            format=self._current_ext(),
            toc=self._toc_chk.isChecked(),
            number_sections=self._numsec_chk.isChecked(),
            highlight=HIGHLIGHT_STYLES[self._highlight_combo.currentIndex()][1],
            engine=self._engine_combo.currentData(),
            margin=self._margin_edit.text().strip(),
        )

    def _save_preset(self) -> None:
        suggested = self._preset_combo.currentData() or ""
        if presets.is_builtin(suggested):
            suggested = ""
        name, ok = QInputDialog.getText(self, tr("Save preset"), tr("Name:"), text=suggested)
        if not ok:
            return
        try:
            presets.save(name, self._current_preset())
        except ValueError as e:
            QMessageBox.warning(self, tr("Preset not saved"), str(e))
            return
        self._reload_presets(select=name.strip())

    def _delete_preset(self) -> None:
        name = self._preset_combo.currentData()
        if not name:
            return
        try:
            presets.delete(name)
        except ValueError as e:
            QMessageBox.warning(self, tr("Preset not deleted"), str(e))
            return
        self._reload_presets()

    def _toggle_settings(self, checked: bool) -> None:
        self._settings_box.setVisible(checked)
        self._settings_btn.setText(tr("Settings ▾") if checked else tr("Settings ▸"))

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
            self._output_label.setText(tr("Output folder:"))
            self._output_btn.setToolTip(tr("Folder for the finished files"))
            self._output_edit.setText(str(Path(paths[0]).parent))
        else:
            self._output_label.setText(tr("Output file:"))
            self._output_btn.setToolTip(tr("Where to save the result"))
            self._output_edit.setText(str(Path(paths[0]).with_suffix(f".{self._current_ext()}")))

    def _on_format_changed(self) -> None:
        current = self._output_edit.text()
        if current and not self._batch():
            self._output_edit.setText(str(Path(current).with_suffix(f".{self._current_ext()}")))
        settings.put("pandoc/format", self._current_ext())
        self._update_pdf_controls()

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
                self, tr("Folder for results"), self._output_edit.text() or settings.last_dir()
            )
            if folder:
                self._output_edit.setText(folder)
            return
        ext = self._current_ext()
        initial = self._output_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save as"), initial, f"{ext.upper()} (*.{ext})"
        )
        if path:
            self._output_edit.setText(path)

    # ------------------------------------------------------------------ run

    def _build_jobs(self) -> list[Job] | None:
        inputs = [p for p in self._inputs.paths() if os.path.isfile(p)]
        missing = self._inputs.count() - len(inputs)
        if missing:
            self._log.append(tr("ℹ Skipped missing files: {n}").format(n=missing))
        if not inputs:
            self._log.append(tr("Select an input file."))
            return None

        target = self._output_edit.text().strip()
        if not target:
            self._log.append(tr("Specify where to save the result."))
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
            self._log.append(tr("ℹ Cancelling — waiting for the files in progress..."))
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
            self._log.append(tr("ℹ Conversion cancelled."))
            return

        out_dir = Path(jobs[0].output_path).parent
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._log.append(tr("✗ Could not create the output folder: {e}").format(e=e))
            return

        opts = self._options()
        self._last_result = jobs[0].output_path if len(jobs) == 1 else str(out_dir)
        self._log.reset()
        ext = self._current_ext()
        self._log.append(
            tr("▶ Converting to .{ext}: {name}").format(ext=ext, name=jobs[0].name)
            if len(jobs) == 1
            else tr("▶ Batch conversion to .{ext}: {n} files").format(ext=ext, n=len(jobs))
        )
        self._convert_btn.setText(tr("Cancel"))

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
        self._convert_btn.setText(tr("Convert"))
        self._convert_btn.setEnabled(True)
        if failed and ok:
            self._log.append(tr("✓ Done: {ok}, failed: {failed}").format(ok=ok, failed=failed))
        elif failed:
            self._log.append(tr("✗ Could not convert files: {failed}").format(failed=failed))
        elif ok == 1:
            self._log.append(tr("✓ Done → {path}").format(path=self._last_result))
        else:
            self._log.append(tr("✓ Done: {ok} files → {path}").format(ok=ok, path=self._last_result))
        if ok:
            self._log.set_result(self._last_result)
