import base64
import hashlib
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_DATA_URI_RE = re.compile(r"data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)")

# mime-подтип → расширение файла, если они не совпадают
_MIME_EXT = {"jpeg": "jpg", "svg+xml": "svg", "x-emf": "emf", "x-wmf": "wmf"}


def decode_data_uris(text: str, media_dir: Path, *, rename_links: bool) -> tuple[str, int]:
    """Декодирует base64-картинки из текста в media_dir.

    Возвращает (текст, число_сохранённых_картинок). Одинаковые картинки
    сохраняются один раз (дедупликация по md5). При rename_links=True
    data-URI в тексте заменяются на относительные ссылки.
    """
    saved: dict[str, str] = {}  # md5 → имя файла

    def _save(subtype: str, b64: str) -> str | None:
        try:
            data = base64.b64decode(b64)
        except Exception:
            return None
        if not data:
            return None
        digest = hashlib.md5(data).hexdigest()
        if digest not in saved:
            ext = _MIME_EXT.get(subtype, subtype)
            name = f"image{len(saved) + 1}.{ext}"
            media_dir.mkdir(parents=True, exist_ok=True)
            (media_dir / name).write_bytes(data)
            saved[digest] = name
        return saved[digest]

    def _replace(m: re.Match) -> str:
        name = _save(m.group(1), m.group(2))
        if name is None:
            return m.group(0)
        return f"{media_dir.name}/{name}" if rename_links else m.group(0)

    new_text = _DATA_URI_RE.sub(_replace, text)
    return new_text, len(saved)


def extract_to_markdown_media(md_path: str) -> int:
    """Извлекает картинки из готового .md в <имя>_media и правит ссылки."""
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    media_dir = Path(str(p.with_suffix("")) + "_media")
    log.debug("Извлечение изображений из %s в %s", md_path, media_dir)
    new_text, count = decode_data_uris(text, media_dir, rename_links=True)
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")
    return count


def extract_images_only(input_path: str, dest_dir: str) -> int:
    """Извлекает изображения из файла в dest_dir через MarkItDown.

    Markdown-результат не сохраняется — нужны только сами картинки.
    """
    from markitdown import MarkItDown
    log.info("Извлечение изображений: вход=%s → папка=%s", input_path, dest_dir)
    result = MarkItDown().convert(input_path, keep_data_uris=True)
    _, count = decode_data_uris(result.text_content, Path(dest_dir), rename_links=False)
    log.info("Извлечение изображений: сохранено %d файлов", count)
    return count
