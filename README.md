# DocForge

Desktop GUI wrapper for [MarkItDown](https://github.com/microsoft/markitdown) and [Pandoc](https://pandoc.org/).
Convert documents between formats without touching the terminal.

[Русская документация](README.ru.md)

---

## Features

### MarkItDown tab

Converts any supported file to Markdown using Microsoft's MarkItDown library.

Supported input: Word, PDF, Excel, PowerPoint, HTML, images (with OCR), and more.

- Output path is suggested automatically (same directory, `.md` extension)
- **Extract images** (optional, on by default): MarkItDown embeds images as base64;
  this option decodes them into an `<output>_media` folder and rewrites links to
  relative paths, so the Markdown renders with images in any viewer
- Optional audio/video support via ffmpeg — one-click install inside the app

### Pandoc tab

Full bidirectional conversion between document formats via Pandoc.

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

### General

- Dark theme
- UTF-8 throughout — Cyrillic and other non-Latin text works out of the box
- Conversion runs in a background thread — UI stays responsive
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
pip install -r requirements.txt
python main.py
```

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

Installed from the setup window, or any time later via the **Install ffmpeg** button
in the MarkItDown tab. The app uses [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)
— no manual download needed. If ffmpeg is already in your system PATH, it is detected automatically.

### MiKTeX — PDF output

Required only for the **PDF** output format in the Pandoc tab. The setup window installs it
via `winget`; you can also install it manually from [miktex.org](https://miktex.org/).

The app prefers the `xelatex` engine (handles Cyrillic) and enables MiKTeX's
on-the-fly package installation automatically, so the first PDF build pulls any
missing LaTeX packages without prompting. The first PDF conversion may therefore
take a minute while those packages download.

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
3. The output path is updated automatically — adjust if needed
4. Click **Convert**

Conversion results and errors appear in the log area at the bottom of each tab.

---

## Logs

A detailed log is written to `%APPDATA%\DocForge\logs\docforge.log` (rotated, with a few
backups). It records each conversion — input file, format, target format, output path,
options, the tool used and its version — and full tracebacks for any error.

The log file path is shown in the status bar at the bottom of the window; click it to open
the folder. When reporting a problem, attach this file.
