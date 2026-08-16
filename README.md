# DocForge

Desktop GUI wrapper for [MarkItDown](https://github.com/microsoft/markitdown) and [Pandoc](https://pandoc.org/).
Convert documents between formats without touching the terminal.

[Русская документация](README.ru.md)

---

## Features

### Batch conversion

Every tab works with one file or many:

- **Обзор** selects several files at once; **Папка** takes every supported file in a folder
- Files (or a whole folder) can be dropped onto the window
- The **▾** button next to the input field reopens one of the last 10 selections
- With one file selected you name the result exactly; with several you pick an output
  folder and names are derived from the sources
- Progress is shown as "3 из 12"; the convert button turns into **Отмена** while a batch
  runs (jobs already started finish, the rest are skipped)
- Jobs run in a small worker pool. PDF output is forced to one at a time — LaTeX and
  Chromium are heavy, and two MiKTeX processes installing packages can clash
- If some results already exist you are asked once for the whole batch: save alongside
  (`name-2`), overwrite, or cancel

### Windows integration (optional)

The **Интеграция** button (top-right corner) offers two shortcuts, both written under
`HKCU` — no administrator rights, and unchecking removes them again:

- **Explorer context menu** — right-click a supported file to open it in DocForge
- **SendTo shortcut** — right-click → Send to → DocForge. Better for several files at
  once: they arrive in a single window as one batch

Files handed over this way land on the tab that fits them (Pandoc when it can read the
format, otherwise MarkItDown).

### MarkItDown tab

Converts any supported file to Markdown using Microsoft's MarkItDown library.

Supported input: Word, PDF, Excel, PowerPoint, HTML, images (with OCR), and more.

- Output path is suggested automatically (same directory, `.md` extension)
- **Extract images** (optional, on by default): MarkItDown embeds images as base64;
  this option decodes them into an `<output>_media` folder and rewrites links to
  relative paths, so the Markdown renders with images in any viewer
- Audio/video support via ffmpeg (optional, installed from the **Components** dialog)

### Pandoc tab

Full bidirectional conversion between document formats via Pandoc.

Options: table of contents (`--toc`), section numbering (`--number-sections`),
syntax-highlighting style for code.

**Presets** keep a named set of these settings. Three come with the app (print-ready PDF,
Word document with a table of contents, Markdown for an LLM); your own are saved with
**Сохранить** and removed with **Удалить** — the built-in ones are protected.

For PDF output you can pick the engine and the page margins (default `2cm`, editable):

- **xelatex** (LaTeX) — classic typesetting, great for formulas; handles Cyrillic
- **Chromium** — renders through a Chromium browser, so the PDF looks like a web page
  (full width, modern CSS); install it from the **Components** dialog

| Output format | Extension |
|---|---|
| Markdown | `.md` |
| HTML | `.html` |
| Word Document | `.docx` |
| EPUB | `.epub` |
| reStructuredText | `.rst` |
| Plain Text | `.txt` |
| LaTeX | `.tex` |
| ODT | `.odt` |
| RTF | `.rtf` |
| PDF | `.pdf` |

- Output file extension updates automatically when the format changes
- Input format is detected automatically from the file extension

### Images tab

Extracts embedded images from a file (Word, PowerPoint, PDF, EPUB, etc.) into a
folder of your choice, without producing any Markdown — just the images. PDF images
are extracted with PyMuPDF; other formats via MarkItDown.

### General

- Dark theme
- Russian and English interface — switch it in the status bar (restart to apply)
- UTF-8 throughout — Cyrillic and other non-Latin text works out of the box
- Conversion runs in a background thread — UI stays responsive
- Browse dialogs show only supported file types by default
- **Components** and **Интеграция** buttons (top-right corner) — manage dependencies and
  Windows shortcuts at any time, not just on first launch
- On first launch a setup window installs MarkItDown and Pandoc automatically and
  lets you opt into the optional components

---

## Requirements

- Windows 10 or 11
- Python 3.10 or newer ([python.org](https://www.python.org/downloads/), tick "Add Python to PATH")
- Internet connection on first launch (downloads the Pandoc binary automatically)
- PDF output additionally needs MiKTeX — the setup window can install it for you

---

## Installation

```bash
git clone https://github.com/Lueur3/docforge.git
cd docforge
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python main.py
```

Dependencies are declared in `pyproject.toml`, so `pip install -e .` installs everything
and also registers a `docforge` command. A virtual environment is optional but recommended.

After that, launch the app by double-clicking **DocForge.bat**.
If the app fails to start, run **DocForge-debug.bat** to see the error message.

On the first launch, a setup window lists every component with its download source.
MarkItDown and Pandoc (required core) are installed automatically; the optional
components — ffmpeg and MiKTeX — have toggles you can switch off.

---

## Optional components

### ffmpeg — audio and video

Enables converting audio and video files in the MarkItDown tab
(e.g. extracting transcripts from `.mp3`, `.mp4`, `.wav`).

Installed from the **Components** dialog (button in the top-right corner), on first launch
or any time later. The app uses [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)
— no manual download needed. If ffmpeg is already in your system PATH, it is detected automatically.

### MiKTeX — PDF output

Required only for the **PDF** output format in the Pandoc tab. The setup window installs it
via `winget`; you can also install it manually from [miktex.org](https://miktex.org/).

The app uses the `xelatex` engine (handles Cyrillic) and enables MiKTeX's
on-the-fly package installation automatically, so the first PDF build pulls any
missing LaTeX packages without prompting. The first PDF conversion may therefore
take a minute while those packages download.

### Chromium — browser-style PDF

An alternative PDF engine that renders through a Chromium browser (via Playwright), so the
PDF looks like a web page — full width, modern CSS — rather than a LaTeX document. Pick it
in the Pandoc tab's **PDF — engine** dropdown. Installed from the **Components** dialog
(`pip install playwright` plus a ~150 MB Chromium download).

---

## Usage

**MarkItDown tab**

1. Click **Browse** and select an input file
2. The output path is filled in automatically
3. Leave **Extract images** on to save embedded images next to the Markdown, or turn it
   off for text only (useful when the Markdown is meant for an LLM)
4. Click **Convert**

**Pandoc tab**

1. Click **Browse** and select an input file
2. Choose an output format from the dropdown
3. Optionally enable table of contents, section numbering, or a code-highlighting style
4. For PDF, choose the engine and margins (enabled only when the format is PDF)
5. The output path is updated automatically — adjust if needed
6. Click **Convert**

**Images tab**

1. Click **Browse** and select a file that contains images
2. Choose the destination folder
3. Click **Extract images**

The status line at the bottom of a tab shows the latest result; **Подробнее** opens the full log of the run in a separate window, and **Папка** opens the result in Explorer.

---

## Logs

A detailed log is written to `%APPDATA%\DocForge\logs\docforge.log` (rotated, with a few
backups). It records each conversion — input file, format, target format, output path,
options, the tool used and its version — and full tracebacks for any error.

The log file path is shown in the status bar at the bottom of the window; click it to open
the folder. When reporting a problem, attach this file.

---

## Project structure

```
main.py                    launcher (run by DocForge.bat)
pyproject.toml             package metadata, dependencies, ruff config
tests/test_smoke.py        offline self-test of all conversion paths
docforge/
  app.py                   entry point: logging, theme, deps, window
  theme.py                 dark theme
  logging_setup.py         file logging
  proc.py                  shared subprocess flag (no console window)
  core/                    logic, no UI
    markitdown.py          file → Markdown
    pandoc.py              Pandoc formats/options + the conversion routine
    batch.py               job queue, worker pool, progress
    presets.py             named Pandoc setting sets
    paths.py               free output names, path comparison
    errors.py              readable wording for file errors
    winintegration.py      Explorer verb + SendTo shortcut (HKCU)
    images.py              image extraction (MarkItDown + PyMuPDF)
    chromium.py            HTML → PDF via Playwright/Chromium
    latex.py               LaTeX engine discovery (MiKTeX)
    ffmpeg.py              ffmpeg discovery
    installer.py           dependency checks + install worker
  ui/                      PyQt6 interface
    window.py              main window
    setup_dialog.py        Components dialog
    widgets.py             status line + log window
    inputs.py              file/folder selector shared by the tabs
    dialogs.py             overwrite-protection prompts
    integration_dialog.py  Windows integration dialog
    file_filters.py        supported extensions + Browse filters
    tabs/                  MarkItDown / Pandoc / Images tabs
  resources/app.ico        application icon
```

