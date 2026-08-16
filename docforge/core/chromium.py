import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def available() -> bool:
    """True if both the playwright package and a Chromium browser are installed.

    The check is cheap (no browser launch): the package imports and the
    ms-playwright cache contains a chromium-* directory.
    """
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    base = Path(os.getenv("LOCALAPPDATA", "")) / "ms-playwright"
    return base.is_dir() and any(base.glob("chromium-*"))


def html_to_pdf(html_path: str, out_pdf: str, margin: str = "") -> None:
    """Render a local HTML file to PDF with the Chromium engine (browser-style)."""
    from playwright.sync_api import sync_playwright

    pdf_kwargs = {"path": out_pdf, "print_background": True, "format": "A4"}
    if margin:
        pdf_kwargs["margin"] = {"top": margin, "right": margin,
                                "bottom": margin, "left": margin}

    log.info("Chromium: рендер %s → %s (поля=%s)", html_path, out_pdf, margin or "по умолч.")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(Path(html_path).as_uri(), wait_until="networkidle")
            page.pdf(**pdf_kwargs)
        finally:
            browser.close()
