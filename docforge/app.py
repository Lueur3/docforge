import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from docforge import i18n
from docforge.core.paths import get_resource_path, init_runtime_environment
from docforge.core.single_instance import SingleInstanceServer, send_to_existing_instance
from docforge.logging_setup import setup_logging
from docforge.theme import apply_dark_theme
from docforge.ui.setup_dialog import ensure_dependencies
from docforge.ui.window import MainWindow

log = logging.getLogger(__name__)


def _deferred_init() -> None:
    """Non-blocking background tasks run after window is visible."""
    try:
        from docforge.core.ffmpeg import configure_pydub, find_ffmpeg
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            configure_pydub(ffmpeg_path)
    except Exception as e:
        log.debug("Фоновая инициализация ffmpeg: %s", e)


def main() -> None:
    log_file = setup_logging()
    init_runtime_environment()

    # files passed on the command line (Explorer context menu / SendTo)
    incoming = [a for a in sys.argv[1:] if os.path.isfile(a)]

    # Check if another DocForge instance is already running
    if send_to_existing_instance(incoming):
        # Forwarded files to running instance, exit immediately
        sys.exit(0)

    # without this Windows shows the Python icon in the taskbar, not ours
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DocForge")

    app = QApplication(sys.argv)
    app.setApplicationName("DocForge")
    # language must be known before any widget takes its text
    i18n.load_language()
    icon_path = get_resource_path("app.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    apply_dark_theme(app)
    ensure_dependencies(app)

    if incoming:
        log.info("Получено файлов из командной строки: %d", len(incoming))

    window = MainWindow(log_file)
    single_server = SingleInstanceServer(window.load_files, window)
    if incoming:
        window.load_files(incoming)
    window.show()
    log.info("Окно показано, лог пишется в %s", log_file)

    # wire pydub/ffmpeg up in the event loop right after showing window
    QTimer.singleShot(0, _deferred_init)

    ret = app.exec()
    single_server.close()
    sys.exit(ret)
