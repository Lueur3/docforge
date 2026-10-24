# DocForge v1.0.0

DocForge is a desktop graphical interface for Microsoft MarkItDown and Pandoc, providing document format conversion without command-line usage.

## Performance and Architecture

- Startup optimization: PyInstaller directory distribution (`--onedir`) replaces single-file extraction, reducing cold launch time to ~200–350 ms.
- Lazy tab loading: Interface tabs (Pandoc, Images) are instantiated on demand, deferring widget construction until navigated to.
- Non-blocking initialization: Auxiliary component discovery (ffmpeg, pydub) is deferred to the event loop after the main window is rendered.

## Packaging and Distribution

- Windows installer (`DocForge-Setup-1.0.0.exe`) built via Inno Setup with desktop, start menu, and "Send to" integration. Installs per-user without requiring administrator privileges (`HKCU`).
- Standalone portable archive (`DocForge-Portable-v1.0.0.zip`) containing the uncompressed executable and bundled runtime dependencies.
- Zero local Python requirement for end users: core runtime and libraries are precompiled.

## Core Features Summary

- **MarkItDown conversion**: Converts Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`), PDF, HTML, and audio/image files to Markdown. Supports automatic base64 image extraction to relative file paths.
- **Pandoc conversion**: Bidirectional conversions across Markdown, HTML, DOCX, PDF, EPUB, LaTeX, RTF, ODT, and plain text. Includes conversion presets and dual PDF backends (XeLaTeX and Chromium).
- **Direct image extraction**: Extracts embedded images directly from PDF, DOCX, and PPTX to a target directory.
- **Batch processing**: Multi-file selection, directory scanning, drag-and-drop, worker pool execution, and file overwrite protection.
- **OS integration**: Optional Windows Explorer context menu and "Send to" menu registration.
- **Localization**: Interface available in English and Russian, switchable via the status bar.

## Installation

- **Installer**: Run `DocForge-Setup-1.0.0.exe` and complete the setup wizard.
- **Portable**: Extract `DocForge-Portable-v1.0.0.zip` and run `DocForge.exe`.
