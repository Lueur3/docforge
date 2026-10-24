# DocForge v1.0.1

DocForge is a desktop graphical interface for Microsoft MarkItDown and Pandoc, providing document format conversion without command-line usage.

## Fixes and Improvements in v1.0.1

- **Immediate cancellation and process termination**: Cancelling conversion jobs now immediately terminates running child processes (including `pandoc.exe`), eliminating background stalls and thread hangs.
- **Pandoc memory guard**: Implemented a 4 GB Haskell RTS heap limit (`+RTS -M4G -RTS`) to prevent pathological input files (such as massive HTML documents with inline base64 images) from consuming excessive physical RAM and causing system thrashing.
- **Large file guidance**: Added a notice for HTML files exceeding 30 MB when targeting Markdown, recommending the MarkItDown tab for faster, memory-efficient processing.
- **System language detection**: The application now detects the Windows display language on first run (Russian on Russian Windows, English for all other system languages).
- **Explorer context menu synchronization**: Changing interface language now automatically updates registered context menu labels in the Windows Registry without requiring manual re-registration.

## Distribution

- **Installer**: `DocForge-Setup-1.0.1.exe` (per-user Inno Setup installer).
- **Portable**: `DocForge-Portable-v1.0.1.zip` (standalone directory archive).

---

## Core Features Overview

- **MarkItDown conversion**: Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`), PDF, HTML, and audio/image files to Markdown with automatic media extraction.
- **Pandoc conversion**: Bidirectional conversions across Markdown, HTML, DOCX, PDF, EPUB, LaTeX, RTF, ODT, and plain text with dual PDF engines (XeLaTeX and Chromium).
- **Image extraction**: Direct extraction of embedded images from PDF, DOCX, and PPTX documents.
- **Batch processing**: Multi-file selection, directory scanning, drag-and-drop, worker pool execution, and file overwrite protection.
- **OS integration**: Optional Windows Explorer context menu and "Send to" menu shortcuts.
- **Performance**: Instant cold startup (~200–350 ms) via onedir distribution and lazy widget initialization.
