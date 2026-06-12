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
- MarkItDown and Pandoc are installed automatically on first launch

---

## Requirements

- Python 3.10 or newer
- Internet connection on first launch (downloads Pandoc binary automatically)
- For PDF output: a LaTeX engine, e.g. [MiKTeX](https://miktex.org/) (Windows) or TeX Live (Linux/macOS)

---

## Installation

```bash
git clone https://github.com/Lueur3/docforge.git
cd docforge
pip install -r requirements.txt
python main.py
```

After that, just double-click **DocForge.bat** — it launches the app without a console window
(via `pythonw`). If the app fails to start, run **DocForge-debug.bat** to see the error.

On the first launch, a setup window lists every component with its download source;
MarkItDown and Pandoc are installed automatically, optional ones can be toggled off.

---

## Optional: ffmpeg

ffmpeg enables conversion of audio and video files in the MarkItDown tab
(e.g. extracting transcripts from `.mp3`, `.mp4`, `.wav`).

**To install:** click the **Install ffmpeg** button in the MarkItDown tab.
The app uses [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — no manual download needed.

If ffmpeg is already present in your system PATH, it will be detected automatically.

---

## Usage

**MarkItDown tab**

1. Click **Browse** and select an input file
2. The output path is filled in automatically
3. Adjust the output path if needed
4. Click **Convert**

**Pandoc tab**

1. Click **Browse** and select an input file
2. Choose an output format from the dropdown
3. The output path is updated automatically — adjust if needed
4. Click **Convert**

Conversion results and errors appear in the log area at the bottom of each tab.
