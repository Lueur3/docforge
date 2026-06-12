import sys
import subprocess

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class _InstallWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    def run(self) -> None:
        steps = [
            ("Установка markitdown...", ["markitdown[all]"]),
            ("Установка pypandoc...",   ["pypandoc"]),
        ]
        for message, packages in steps:
            self.status.emit(message)
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--quiet", *packages],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as e:
                self.done.emit(False, f"Ошибка установки {packages[0]}: {e}")
                return

        self.status.emit("Загрузка Pandoc (может занять минуту)...")
        try:
            import pypandoc
            pypandoc.download_pandoc()
        except Exception as e:
            self.done.emit(False, f"Ошибка загрузки Pandoc: {e}")
            return

        self.done.emit(True, "")


class _InstallDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocForge — установка зависимостей")
        self.setFixedSize(420, 110)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self._label = QLabel("Подготовка...", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._bar = QProgressBar(self)
        self._bar.setRange(0, 0)  # indeterminate

        layout.addWidget(self._label)
        layout.addWidget(self._bar)

        self._worker = _InstallWorker()
        self._worker.status.connect(self._label.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool, error: str) -> None:
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка установки", error)
            sys.exit(1)


def _check() -> tuple[bool, bool]:
    """Возвращает (markitdown_ok, pandoc_ok)."""
    markitdown_ok = False
    pandoc_ok = False

    try:
        import markitdown  # noqa: F401
        markitdown_ok = True
    except ImportError:
        pass

    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        pandoc_ok = True
    except Exception:
        pass

    return markitdown_ok, pandoc_ok


def ensure_dependencies(_app: QApplication) -> None:
    """Проверяет зависимости и при необходимости устанавливает их."""
    md_ok, pandoc_ok = _check()
    if md_ok and pandoc_ok:
        return

    dialog = _InstallDialog()
    dialog.exec()
