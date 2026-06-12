import shutil
import subprocess
import sys
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal


def find_ffmpeg() -> Optional[str]:
    """Ищет ffmpeg: сначала в системном PATH, потом в imageio-ffmpeg."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        return None


def configure_pydub(ffmpeg_path: str) -> None:
    """Указывает pydub на нужный бинарник ffmpeg."""
    try:
        import pydub
        pydub.AudioSegment.converter = ffmpeg_path
    except ImportError:
        pass


class FfmpegInstallWorker(QThread):
    done = pyqtSignal(bool, str)  # (success, ffmpeg_path | error_message)

    def run(self) -> None:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "imageio-ffmpeg", "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            self.done.emit(False, f"pip install завершился с ошибкой: {e}")
            return

        path = find_ffmpeg()
        if path:
            self.done.emit(True, path)
        else:
            self.done.emit(False, "Пакет установлен, но ffmpeg не обнаружен")
