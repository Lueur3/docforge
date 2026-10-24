import logging
import logging.handlers
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

LOG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "DocForge" / "logs"
LOG_FILE = LOG_DIR / "docforge.log"

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s.%(funcName)s:%(lineno)d | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Third-party libraries at DEBUG emit thousands of lines (pdfminer especially,
# while reading a PDF) — that floods the log and slows conversion down badly.
_NOISY_LOGGERS = (
    "pdfminer", "pdfplumber", "PIL", "fontTools", "markdown_it",
    "urllib3", "charset_normalizer", "matplotlib", "comtypes",
)


def _log_environment(log: logging.Logger) -> None:
    import platform
    log.info("=" * 70)
    log.info("DocForge — старт сессии")
    log.info("ОС: %s", platform.platform())
    log.info("Python: %s (%s)", platform.python_version(), sys.executable)
    if getattr(sys, "frozen", False):
        log.info("Режим: скомпилированный standalone (.exe)")
    for pkg in ("PyQt6", "markitdown", "pypandoc", "pymupdf", "imageio-ffmpeg", "playwright"):
        try:
            log.info("Пакет %s: %s", pkg, version(pkg))
        except (PackageNotFoundError, Exception):
            pass


def _qt_message_handler(mode, context, message: str) -> None:
    """Route Qt's internal warnings into our log."""
    logging.getLogger("Qt").warning("%s", message)


def setup_logging() -> Path:
    """Configure the root logger: rotating file + console (when there is one).

    Returns the log file path. Safe to call more than once.
    """
    root = logging.getLogger()
    if root.handlers:  # already configured
        return LOG_FILE

    fmt = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    root.setLevel(logging.DEBUG)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError as e:
        if sys.stderr is not None:
            fallback = logging.StreamHandler(sys.stderr)
            fallback.setLevel(logging.DEBUG)
            fallback.setFormatter(fmt)
            root.addHandler(fallback)
        root.warning("Не удалось инициализировать файл лога %s: %s", LOG_FILE, e)

    for noisy in _NOISY_LOGGERS:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # a console only exists when started via python/DocForge-debug.bat;
    # under pythonw sys.stderr is None, so no console handler is needed
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        root.addHandler(console)

    # uncaught exceptions go to the log with a full traceback
    def _excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger("uncaught").critical(
            "Необработанное исключение", exc_info=(exc_type, exc_value, exc_tb)
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    try:
        from PyQt6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(_qt_message_handler)
    except Exception:
        pass

    _log_environment(logging.getLogger(__name__))
    return LOG_FILE
