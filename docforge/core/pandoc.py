"""Pandoc format and option tables (data only, no UI)."""

# Pandoc code-highlight styles; "" means don't pass the flag (engine default),
# "--no-highlight" disables highlighting altogether.
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

# Output formats: (display name, pandoc writer, extension, needs --standalone).
# Pandoc always reads and writes UTF-8 — no encoding flags required.
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
