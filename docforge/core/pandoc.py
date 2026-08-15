"""Справочные данные форматов и опций Pandoc (без UI)."""

# Стили подсветки кода Pandoc; "" — не передавать флаг (стиль по умолчанию),
# "--no-highlight" — отключить подсветку.
HIGHLIGHT_STYLES = [
    ("По умолчанию", ""),
    ("pygments", "pygments"),
    ("tango", "tango"),
    ("kate", "kate"),
    ("monochrome", "monochrome"),
    ("breezedark", "breezedark"),
    ("espresso", "espresso"),
    ("zenburn", "zenburn"),
    ("haddock", "haddock"),
    ("Без подсветки", "--no-highlight"),
]

# Форматы вывода: (отображаемое имя, writer для pandoc, расширение, флаг --standalone).
# Pandoc всегда читает и пишет UTF-8 — отдельные флаги кодировки не нужны.
FORMATS: list[tuple[str, str, str, bool]] = [
    ("Markdown",         "markdown", "md",   False),
    ("HTML",             "html",     "html", True),
    ("Word Document",    "docx",     "docx", False),
    ("EPUB",             "epub",     "epub", True),
    ("reStructuredText", "rst",      "rst",  False),
    ("Plain Text",       "plain",    "txt",  False),
    ("LaTeX",            "latex",    "tex",  True),
    ("ODT",              "odt",      "odt",  False),
    ("RTF",              "rtf",      "rtf",  True),
    ("PDF",              "pdf",      "pdf",  False),
]
