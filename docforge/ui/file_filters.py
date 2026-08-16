"""Supported input extensions — one source of truth for dialogs and folder scans."""
from docforge.i18n import tr

# MarkItDown: documents, spreadsheets, web, images, archives, audio
MARKITDOWN_EXTS = [
    "pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "csv", "json",
    "xml", "txt", "md", "epub", "jpg", "jpeg", "png", "gif", "bmp", "tiff",
    "webp", "mp3", "wav", "m4a", "zip",
]

# Pandoc: the formats it can read
PANDOC_EXTS = [
    "md", "markdown", "docx", "odt", "epub", "html", "htm", "rst", "tex",
    "latex", "txt", "rtf", "csv", "json", "org", "ipynb",
]

# Image extraction: formats that carry embedded images
IMAGES_EXTS = ["docx", "pptx", "xlsx", "pdf", "odt", "epub", "html", "htm"]


def _filter(title: str, exts: list[str]) -> str:
    mask = " ".join(f"*.{e}" for e in exts)
    return f"{title} ({mask});;" + tr("All files") + " (*)"


# Built on demand, not at import time: the UI language is only known after
# the settings have been read.
def markitdown_filter() -> str:
    return _filter(tr("Supported files"), MARKITDOWN_EXTS)


def pandoc_filter() -> str:
    return _filter(tr("Supported files"), PANDOC_EXTS)


def images_filter() -> str:
    return _filter(tr("Files with images"), IMAGES_EXTS)
