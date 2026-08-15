import logging
import os
from pathlib import Path

from docforge.core import images

log = logging.getLogger(__name__)

# Текстовые форматы, для которых автоопределение кодировки может ошибаться
# (charset-normalizer на системах с не-латинской локалью путает UTF-8 с cp125x)
_TEXT_EXTENSIONS = {".html", ".htm", ".txt", ".md", ".csv", ".json", ".xml"}


def _is_valid_utf8(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            f.read().decode("utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


def convert_to_markdown(input_path: str, output_path: str,
                        extract_images: bool = False) -> int:
    """Конвертирует файл в Markdown. Возвращает число извлечённых картинок."""
    from markitdown import MarkItDown, StreamInfo
    ext = Path(input_path).suffix.lower()
    size = os.path.getsize(input_path) if os.path.isfile(input_path) else -1
    log.info(
        "MarkItDown: вход=%s (формат=%s, размер=%d Б) → выход=%s, извлечение_картинок=%s",
        input_path, ext, size, output_path, extract_images,
    )
    kwargs = {}
    if ext in _TEXT_EXTENSIONS and _is_valid_utf8(input_path):
        kwargs["stream_info"] = StreamInfo(charset="utf-8")
        log.debug("MarkItDown: применена подсказка кодировки UTF-8")
    if extract_images:
        # иначе MarkItDown пишет обрезанный 'data:image/png;base64...'
        kwargs["keep_data_uris"] = True
    result = MarkItDown().convert(input_path, **kwargs)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)
    log.info("MarkItDown: записано %d символов в %s", len(result.text_content), output_path)
    if extract_images:
        count = images.extract_to_markdown_media(output_path)
        log.info("MarkItDown: извлечено изображений: %d", count)
        return count
    return 0
