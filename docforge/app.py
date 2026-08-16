import logging
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from docforge import i18n
from docforge.logging_setup import setup_logging
from docforge.theme import apply_dark_theme
from docforge.ui.setup_dialog import ensure_dependencies
from docforge.ui.window import MainWindow

log = logging.getLogger(__name__)

_ICON = Path(__file__).parent / "resources" / "app.ico"


def main() -> None:
    log_file = setup_logging()

    # without this Windows shows the Python icon in the taskbar, not ours
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DocForge")

    app = QApplication(sys.argv)
    app.setApplicationName("DocForge")
    # language must be known before any widget takes its text
    i18n.load_language()
    if _ICON.is_file():
        app.setWindowIcon(QIcon(str(_ICON)))

    apply_dark_theme(app)
    ensure_dependencies(app)

    # wire pydub up if ffmpeg is already installed
    from docforge.core.ffmpeg import find_ffmpeg, configure_pydub
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        configure_pydub(ffmpeg_path)

    # files passed on the command line (Explorer context menu / SendTo)
    incoming = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if incoming:
        log.info("Получено файлов из командной строки: %d", len(incoming))

    window = MainWindow(log_file)
    if incoming:
        window.load_files(incoming)
    window.show()
    log.info("Окно показано, лог пишется в %s", log_file)
    sys.exit(app.exec())
