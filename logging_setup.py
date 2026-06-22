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


def _log_environment(log: logging.Logger) -> None:
    import platform
    log.info("=" * 70)
    log.info("DocForge — старт сессии")
    log.info("ОС: %s", platform.platform())
    log.info("Python: %s (%s)", platform.python_version(), sys.executable)
    for pkg in ("PyQt6", "markitdown", "pypandoc", "imageio-ffmpeg"):
        try:
            log.info("Пакет %s: %s", pkg, version(pkg))
        except PackageNotFoundError:
            log.info("Пакет %s: не установлен", pkg)
    try:
        import pypandoc
        log.info("Pandoc (бинарник): %s", pypandoc.get_pandoc_version())
    except Exception as e:
        log.info("Pandoc (бинарник): недоступен (%s)", e)


def _qt_message_handler(mode, context, message: str) -> None:
    """Перенаправляет внутренние предупреждения Qt в лог."""
    logging.getLogger("Qt").warning("%s", message)


def setup_logging() -> Path:
    """Настраивает корневой логгер: файл с ротацией + консоль (если есть).

    Возвращает путь к файлу лога. Безопасно при повторном вызове.
    """
    root = logging.getLogger()
    if root.handlers:  # уже настроен
        return LOG_FILE

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Сторонние библиотеки на DEBUG генерируют тысячи строк (особенно pdfminer
    # при чтении PDF) — это забивает лог и сильно замедляет конвертацию.
    # Глушим их до WARNING, наши модули остаются на DEBUG.
    for noisy in ("pdfminer", "pdfplumber", "PIL", "fontTools", "markdown_it",
                  "urllib3", "charset_normalizer", "matplotlib", "comtypes"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # консоль доступна только при запуске через python/DocForge-debug.bat;
    # под pythonw sys.stderr is None — тогда консольный обработчик не нужен
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        root.addHandler(console)

    # необработанные исключения — в лог с полным трейсбеком
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
