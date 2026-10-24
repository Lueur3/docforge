"""Job queue for batch conversion: a worker pool plus progress reporting."""
import contextlib
import logging
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal

from docforge.core.errors import friendly_error
from docforge.i18n import tr

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Job:
    """One conversion: source file → result path."""
    input_path: str
    output_path: str

    @property
    def name(self) -> str:
        return Path(self.input_path).name


def pool_size(job_count: int, *, heavy: bool) -> int:
    """How many jobs to run at once.

    heavy=True (PDF via LaTeX/Chromium) forces a single worker: those engines
    are resource-hungry, and two MiKTeX processes installing packages at the
    same time can clash. Everything else runs a small pool — pandoc spends its
    time in a subprocess, so threads there actually overlap.
    """
    if heavy:
        return 1
    return max(1, min(4, os.cpu_count() or 1, job_count))


class BatchRunner(QThread):
    """Runs a list of jobs and reports progress.

    `fn` performs one conversion and raises on failure. Every signal is emitted
    from this thread, so the GUI receives them safely.
    """

    progress    = pyqtSignal(int, int, str)  # done, total, current file name
    message     = pyqtSignal(str)            # a line for the log
    completed   = pyqtSignal(int, int)       # succeeded, failed

    def __init__(self, jobs: list[Job], fn: Callable[..., None],
                 max_workers: int = 1) -> None:
        super().__init__()
        self._jobs = jobs
        self._fn = fn
        self._max_workers = max(1, max_workers)
        self._cancelled = False
        self._active_procs: set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    def register_process(self, proc: subprocess.Popen) -> None:
        with self._lock:
            if self._cancelled:
                with contextlib.suppress(Exception):
                    proc.kill()
            else:
                self._active_procs.add(proc)

    def unregister_process(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._active_procs.discard(proc)

    def cancel(self) -> None:
        """Stop pending jobs and immediately terminate all running processes."""
        self._cancelled = True
        log.info("Пакетная обработка: запрошена немедленная отмена")
        with self._lock:
            for proc in list(self._active_procs):
                try:
                    log.info("Принудительное завершение процесса PID %s", proc.pid)
                    proc.kill()
                except Exception as e:
                    log.debug("Ошибка при kill: %s", e)

    def _guarded(self, job: Job) -> None:
        if self._cancelled:
            raise RuntimeError(tr("cancelled by the user"))

        def on_proc(proc: subprocess.Popen) -> None:
            self.register_process(proc)

        try:
            self._fn(job, on_proc=on_proc)
        except TypeError:
            self._fn(job)

        if self._cancelled:
            raise RuntimeError(tr("cancelled by the user"))

    def run(self) -> None:
        total = len(self._jobs)
        ok = failed = 0
        log.info("Пакетная обработка: %d задач, воркеров: %d", total, self._max_workers)
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(self._guarded, job): job for job in self._jobs}
            for done, future in enumerate(as_completed(futures), start=1):
                job = futures[future]
                try:
                    future.result()
                    ok += 1
                    if total > 1:
                        self.message.emit(f"✓ {job.name}")
                except Exception as e:
                    failed += 1
                    if self._cancelled:
                        self.message.emit(f"✗ {job.name}: {tr('cancelled by the user')}")
                    else:
                        log.exception("Пакетная обработка: ошибка на %s", job.input_path)
                        self.message.emit(f"✗ {job.name}: {friendly_error(e)}")
                self.progress.emit(done, total, job.name)
        log.info("Пакетная обработка: успешно %d, с ошибкой %d", ok, failed)
        self.completed.emit(ok, failed)
