"""Extension filters for QFileDialog — show only files that can be handled."""

_ALL = "Все файлы (*)"


def _filter(title: str, exts: list[str]) -> str:
    mask = " ".join(f"*.{e}" for e in exts)
    return f"{title} ({mask});;{_ALL}"


# MarkItDown: documents, spreadsheets, web, images, archives, audio
MARKITDOWN_INPUT = _filter(
    "Поддерживаемые файлы",
    ["pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "csv", "json",
     "xml", "txt", "md", "epub", "jpg", "jpeg", "png", "gif", "bmp", "tiff",
     "webp", "mp3", "wav", "m4a", "zip"],
)

# Pandoc: the formats it can read
PANDOC_INPUT = _filter(
    "Поддерживаемые файлы",
    ["md", "markdown", "docx", "odt", "epub", "html", "htm", "rst", "tex",
     "latex", "txt", "rtf", "csv", "json", "org", "ipynb"],
)

# Image extraction: formats that carry embedded images
IMAGES_INPUT = _filter(
    "Файлы с изображениями",
    ["docx", "pptx", "xlsx", "pdf", "odt", "epub", "html", "htm"],
)
