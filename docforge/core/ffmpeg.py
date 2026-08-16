import logging
import shutil
from typing import Optional

log = logging.getLogger(__name__)


def find_ffmpeg() -> Optional[str]:
    """Look for ffmpeg: system PATH first, then the imageio-ffmpeg binary."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        return None


def configure_pydub(ffmpeg_path: str) -> None:
    """Point pydub at the ffmpeg binary we found."""
    try:
        import pydub
        pydub.AudioSegment.converter = ffmpeg_path
    except ImportError:
        pass
