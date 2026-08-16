"""Pandoc format tables and the conversion routine itself."""
import contextlib
import logging
import os
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from docforge.core import chromium, latex

log = logging.getLogger(__name__)

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

# Writers whose images are pulled out into a folder next to the result
_MEDIA_WRITERS = ("markdown", "rst", "latex")


class PandocError(RuntimeError):
    """A conversion failed; the message is meant for the user."""


@dataclass
class PandocOptions:
    """Everything the Pandoc tab can configure for one run."""
    writer: str
    standalone: bool = False
    toc: bool = False
    number_sections: bool = False
    highlight: str = ""
    pdf_engine: str = "chromium"
    margin: str = ""

    @property
    def is_pdf(self) -> bool:
        return self.writer == "pdf"

    @property
    def is_heavy(self) -> bool:
        """PDF engines (LaTeX/Chromium) must not run several at a time."""
        return self.is_pdf


def _relativize_media_paths(output_path: str, media_dir: str) -> None:
    """Rewrite absolute image paths in the result as relative ones.

    Pandoc writes the --extract-media path verbatim, so the links break when
    the file is moved and fail to render in most viewers.
    """
    out = Path(output_path)
    try:
        text = out.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    rel = os.path.basename(media_dir)
    fwd = media_dir.replace("\\", "/")
    variants = {media_dir, fwd, urllib.parse.quote(fwd, safe=":/")}
    new_text = text
    for v in variants:
        new_text = new_text.replace(v, rel)
    if new_text != text:
        out.write_text(new_text, encoding="utf-8")


def _convert_via_chromium(input_path: str, output_path: str, opts: PandocOptions,
                          say: Callable[[str], None]) -> None:
    """PDF via Chromium: pandoc makes a self-contained HTML, Chromium prints it."""
    import pypandoc

    if not chromium.available():
        log.warning("Pandoc: Chromium/Playwright не установлен")
        raise PandocError(
            "движок Chromium не установлен — установите его в диалоге «Компоненты»"
        )

    tmp_html = None
    try:
        if Path(input_path).suffix.lower() in (".html", ".htm"):
            html_path = input_path
        else:
            fd, tmp_html = tempfile.mkstemp(suffix=".html")
            os.close(fd)
            pypandoc.convert_file(
                input_path, "html", outputfile=tmp_html,
                extra_args=["--standalone", "--embed-resources"],
            )
            html_path = tmp_html
        say("▶ PDF-движок: Chromium")
        chromium.html_to_pdf(html_path, output_path, opts.margin)
    finally:
        if tmp_html and os.path.exists(tmp_html):
            with contextlib.suppress(OSError):
                os.remove(tmp_html)


def _build_args(output_path: str, opts: PandocOptions,
                say: Callable[[str], None]) -> tuple[list[str], Optional[str]]:
    """Assemble pandoc arguments. Returns (extra_args, media_dir or None)."""
    extra = ["--standalone"] if opts.standalone else []

    if opts.is_pdf:
        engine = latex.find_pdf_engine()
        if engine is None:
            log.warning("Pandoc: PDF-движок не найден")
            raise PandocError(
                "для вывода в PDF нужен LaTeX-движок — установите MiKTeX "
                "(https://miktex.org), приложение найдёт его автоматически"
            )
        log.info("Pandoc: PDF-движок=%s", engine)
        say(f"▶ PDF-движок: {engine}")
        latex.ensure_autoinstall(engine)
        extra.append(f"--pdf-engine={engine}")
        if latex.is_unicode_engine(engine):
            # a system font that covers Cyrillic
            extra += ["-V", "mainfont=Segoe UI"]
        if opts.margin:
            extra += ["-V", f"geometry:margin={opts.margin}"]
    elif opts.writer == "html":
        # images from docx/odt/epub get embedded straight into the html
        extra.append("--embed-resources")

    media_dir: Optional[str] = None
    if opts.writer in _MEDIA_WRITERS:
        # images are extracted into a folder next to the output file
        media_dir = str(Path(output_path).with_suffix("")) + "_media"
        extra.append(f"--extract-media={media_dir}")

    # user-selected options
    if opts.toc:
        extra.append("--toc")
        if "--standalone" not in extra:
            extra.append("--standalone")  # a TOC needs a full document
    if opts.number_sections:
        extra.append("--number-sections")
    if opts.highlight == "--no-highlight":
        extra.append("--no-highlight")
    elif opts.highlight:
        extra.append(f"--highlight-style={opts.highlight}")

    return extra, media_dir


def convert(input_path: str, output_path: str, opts: PandocOptions,
            say: Callable[[str], None] = lambda _m: None) -> None:
    """Convert one file with Pandoc. Raises on failure.

    `say` receives progress lines meant for the user-visible log.
    """
    import pypandoc

    in_ext = Path(input_path).suffix.lower()
    size = os.path.getsize(input_path) if os.path.isfile(input_path) else -1
    log.info(
        "Pandoc: вход=%s (формат=%s, размер=%d Б) → writer=%s, выход=%s, standalone=%s",
        input_path, in_ext, size, opts.writer, output_path, opts.standalone,
    )

    # Chromium takes a separate route: pandoc makes HTML, Chromium prints the PDF
    if opts.is_pdf and opts.pdf_engine == "chromium":
        _convert_via_chromium(input_path, output_path, opts, say)
        log.info("Pandoc/Chromium: готово → %s", output_path)
        return

    extra, media_dir = _build_args(output_path, opts, say)

    writer = opts.writer
    if writer == "markdown":
        # no pandoc {width=...} attributes and no raw-HTML <img> —
        # otherwise the images don't render in common viewers
        writer = "markdown-link_attributes-raw_html"

    log.debug("Pandoc: pypandoc.convert_file writer=%s extra_args=%s", writer, extra)
    try:
        pypandoc.convert_file(input_path, writer, outputfile=output_path, extra_args=extra)
    except Exception as e:
        msg = str(e)
        if opts.is_pdf and "package" in msg.lower():
            raise PandocError(
                f"{msg}\nПохоже, MiKTeX не хватает LaTeX-пакетов: откройте MiKTeX Console → "
                "Settings и включите 'Always install missing packages on-the-fly'"
            ) from e
        raise

    if media_dir and os.path.isdir(media_dir):
        _relativize_media_paths(output_path, media_dir)
        say(f"ℹ Картинки извлечены в: {media_dir}")

    log.info("Pandoc: готово → %s", output_path)
