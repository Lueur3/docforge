import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from docforge.logging_setup import setup_logging
from docforge.theme import apply_dark_theme
from docforge.ui.setup_dialog import ensure_dependencies
from docforge.ui.window import MainWindow

log = logging.getLogger(__name__)

_ICON = Path(__file__).parent / "resources" / "app.ico"


def main() -> None:
    log_file = setup_logging()

    # без этого Windows показывает в панели задач иконку Python, а не приложения
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DocForge")

    app = QApplication(sys.argv)
    app.setApplicationName("DocForge")
    if _ICON.is_file():
        app.setWindowIcon(QIcon(str(_ICON)))

    apply_dark_theme(app)
    ensure_dependencies(app)

    # настраиваем pydub, если ffmpeg уже установлен
    from docforge.core.ffmpeg import find_ffmpeg, configure_pydub
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        configure_pydub(ffmpeg_path)

    window = MainWindow(log_file)
    window.show()
    log.info("Окно показано, лог пишется в %s", log_file)
    sys.exit(app.exec())
