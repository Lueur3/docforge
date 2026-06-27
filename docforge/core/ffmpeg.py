import logging
import shutil
from typing import Optional

log = logging.getLogger(__name__)


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
