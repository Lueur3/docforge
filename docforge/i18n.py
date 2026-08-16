"""Tiny translation layer: English source strings, Russian looked up in a dict.

No Qt Linguist toolchain — the app has two languages and a few hundred strings,
so a plain dict keeps everything editable in one file and needs no build step.
Untranslated text falls back to the English source, so a missing entry degrades
gracefully instead of showing an empty label.
"""
import logging

log = logging.getLogger(__name__)

LANGUAGES = {"ru": "Русский", "en": "English"}
DEFAULT = "ru"

_current = DEFAULT


def current() -> str:
    return _current


def set_language(code: str) -> None:
    global _current
    if code not in LANGUAGES:
        log.warning("Неизвестный язык «%s», используется %s", code, DEFAULT)
        code = DEFAULT
    _current = code
    log.info("Язык интерфейса: %s", code)


def load_language() -> str:
    """Restore the saved language (called once at startup)."""
    from docforge import settings
    set_language(settings.get_str("ui/language", DEFAULT))
    return _current


def tr(text: str) -> str:
    """Translate a source string into the current language."""
    if _current == "en":
        return text
    return RU.get(text, text)


# English source → Russian. Keys must match the tr() literals exactly.
RU: dict[str, str] = {
    # --- window, common buttons -------------------------------------------
    "Components": "Компоненты",
    "Integration": "Интеграция",
    "Install or check ffmpeg, MiKTeX, Chromium and the core":
        "Установить или проверить ffmpeg, MiKTeX, Chromium и ядро",
    "Explorer context-menu entry and a SendTo shortcut":
        "Пункт в контекстном меню Проводника и ярлык «Отправить»",
    "Log: ": "Лог: ",
    "Interface language": "Язык интерфейса",
    "Browse": "Обзор",
    "Folder": "Папка",
    "Cancel": "Отмена",
    "Save": "Сохранить",
    "Delete": "Удалить",
    "Apply": "Применить",
    "Close": "Закрыть",
    "Continue": "Продолжить",
    "Install": "Установить",
    "Details": "Подробнее",

    # --- input selector ----------------------------------------------------
    "Path to a file, or several files...": "Путь к файлу или несколько файлов...",
    "Select one or more files (Ctrl+O). Files can also be dropped onto the window.":
        "Выбрать один или несколько файлов (Ctrl+O). Файлы также можно перетащить в окно.",
    "Take every supported file from a folder":
        "Взять все поддерживаемые файлы из папки",
    "Recent files": "Недавние файлы",
    "Nothing yet": "Пока пусто",
    "  (missing)": "  (нет на диске)",
    "Select files": "Выбрать файлы",
    "Select a folder with files": "Выбрать папку с файлами",
    "{n} files: ": "{n} файлов: ",

    # --- status log --------------------------------------------------------
    "Open the full conversion log": "Открыть полный лог конвертации",
    "Open the result folder": "Открыть папку с результатом",
    "DocForge — conversion log": "DocForge — лог конвертации",
    "▶ {done} of {total}: {name}": "▶ {done} из {total}: {name}",

    # --- tabs: shared ------------------------------------------------------
    "Input files:": "Входные файлы:",
    "Output file:": "Выходной файл:",
    "Output folder:": "Папка результата:",
    "Path to the result file...": "Путь к файлу результата...",
    "Where to save the result": "Куда сохранить результат",
    "Folder for the finished files": "Папка, куда сложить готовые файлы",
    "Convert": "Конвертировать",
    "Save as": "Сохранить как",
    "Folder for results": "Папка для результатов",
    "Select an input file.": "Укажите входной файл.",
    "Specify where to save the result.": "Укажите, куда сохранить результат.",
    "ℹ Skipped missing files: {n}": "ℹ Пропущено несуществующих файлов: {n}",
    "ℹ Conversion cancelled.": "ℹ Конвертация отменена.",
    "ℹ Cancelling — waiting for the files in progress...":
        "ℹ Отмена — ждём завершения текущих файлов...",
    "✗ Could not create the output folder: {e}":
        "✗ Не удалось создать папку результата: {e}",
    "▶ Converting: {name}": "▶ Конвертация: {name}",
    "▶ Batch conversion: {n} files": "▶ Пакетная конвертация: {n} файлов",
    "✓ Done: {ok}, failed: {failed}": "✓ Готово: {ok}, с ошибкой: {failed}",
    "✗ Could not convert files: {failed}": "✗ Не удалось конвертировать файлов: {failed}",
    "✓ Done → {path}": "✓ Готово → {path}",
    "✓ Done: {ok} files → {path}": "✓ Готово: {ok} файлов → {path}",

    # --- MarkItDown tab ----------------------------------------------------
    "Output file (.md):": "Выходной файл (.md):",
    "Extract images into a folder next to the file":
        "Извлекать изображения в папку рядом с файлом",
    "Folder for the finished .md files": "Папка, куда сложить готовые .md",
    "ℹ Images extracted: {n} → {path}": "ℹ Извлечено изображений: {n} → {path}",

    # --- Pandoc tab --------------------------------------------------------
    "Output format:": "Формат вывода:",
    "Settings ▸": "Настройки ▸",
    "Settings ▾": "Настройки ▾",
    "Preset:": "Пресет:",
    "A ready-made set of settings — applied on selection":
        "Готовый набор настроек — применяется при выборе",
    "Save the current settings as a preset":
        "Сохранить текущие настройки как пресет",
    "Delete the selected preset (built-in ones cannot be removed)":
        "Удалить выбранный пресет (встроенные удалить нельзя)",
    "— none —": "— не выбран —",
    "Save preset": "Сохранить пресет",
    "Name:": "Название:",
    "Preset not saved": "Пресет не сохранён",
    "Preset not deleted": "Пресет не удалён",
    "Table of contents": "Оглавление",
    "Number sections": "Нумерация разделов",
    "Code highlighting:": "Подсветка кода:",
    "PDF — engine:": "PDF — движок:",
    "margins:": "поля:",
    "For example: 2cm, 1.5cm, 1in, 20mm. Empty — the engine's own margins.":
        "Например: 2cm, 1.5cm, 1in, 20mm. Пусто — поля движка по умолчанию.",
    "Chromium (browser-style)": "Chromium (как браузер)",
    "xelatex (LaTeX)": "xelatex (LaTeX)",
    "▶ Converting to .{ext}: {name}": "▶ Конвертация в .{ext}: {name}",
    "▶ Batch conversion to .{ext}: {n} files":
        "▶ Пакетная конвертация в .{ext}: {n} файлов",
    "▶ PDF engine: {engine}": "▶ PDF-движок: {engine}",
    "ℹ Images extracted to: {path}": "ℹ Картинки извлечены в: {path}",

    # --- Images tab --------------------------------------------------------
    "Extracting images from files (docx, pptx, pdf, epub and others)":
        "Извлечение изображений из файлов (docx, pptx, pdf, epub и др.)",
    "Image folder:": "Папка для изображений:",
    "Folder for the per-file image folders:":
        "Папка для подпапок с изображениями:",
    "Where to save the images...": "Куда сохранить картинки...",
    "Save folder (the <file>_images name is added automatically)":
        "Папка для сохранения (имя <файл>_images добавляется само)",
    "Extract images": "Извлечь изображения",
    "Images": "Изображения",
    "Select a save folder": "Выбрать папку для сохранения",
    "Specify a folder for the images.": "Укажите папку для изображений.",
    "▶ Extracting from: {name}": "▶ Извлечение из: {name}",
    "▶ Batch extraction: {n} files": "▶ Пакетное извлечение: {n} файлов",
    "ℹ Extraction cancelled.": "ℹ Извлечение отменено.",
    "✓ Images extracted: {n} → {path}": "✓ Извлечено изображений: {n} → {path}",
    "ℹ No embedded images found in the file.":
        "ℹ В файле не найдено встроенных изображений.",
    "✓ Processed: {ok}, failed: {failed}": "✓ Обработано: {ok}, с ошибкой: {failed}",
    "✗ Could not process files: {failed}": "✗ Не удалось обработать файлов: {failed}",

    # --- overwrite protection ---------------------------------------------
    "Path conflict": "Совпадение путей",
    "The result file is the same as the source — converting would destroy the "
    "original.\n\nChange the output path.":
        "Файл результата совпадает с исходным — конвертация уничтожила бы оригинал.\n\n"
        "Измените путь результата.",
    "Skipped files: {n} — the result would have replaced the source file.":
        "Пропущено файлов: {n} — результат совпал бы с исходным файлом.",
    "The result already exists": "Результат уже существует",
    "Results already exist": "Результаты уже существуют",
    "File": "Файл",
    "Folder ": "Папка",
    "{what} already exists:\n{path}": "{what} уже существует:\n{path}",
    "Save alongside as «{name}» or overwrite?":
        "Сохранить рядом как «{name}» или перезаписать?",
    "Save as {name}": "Сохранить как {name}",
    "Overwrite": "Перезаписать",
    "Already exists: {n} of {total}.": "Уже существует: {n} из {total}.",
    "Save them alongside under free names, or overwrite?":
        "Сохранить их рядом под свободными именами или перезаписать?",
    "Save alongside": "Сохранить рядом",

    # --- components dialog -------------------------------------------------
    "DocForge — component setup": "DocForge — настройка компонентов",
    "DocForge — components": "DocForge — компоненты",
    "DocForge uses external components. Below is what will be downloaded and "
    "from where. The optional ones can be switched off.":
        "DocForge использует внешние компоненты. Ниже показано, что и откуда "
        "будет загружено. Необязательные компоненты можно отключить.",
    "MarkItDown + Pandoc — the conversion core":
        "MarkItDown + Pandoc — ядро конвертации",
    "ffmpeg — audio and video in the MarkItDown tab":
        "ffmpeg — аудио и видео во вкладке MarkItDown",
    "MiKTeX — PDF output in the Pandoc tab (LaTeX engine)":
        "MiKTeX — вывод в PDF во вкладке Pandoc (движок LaTeX)",
    "Chromium — browser-style PDF in the Pandoc tab":
        "Chromium — PDF «как браузер» во вкладке Pandoc",
    "Source: {source}": "Источник: {source}",
    "  —  ✓ already installed": "  —  ✓ уже установлено",
    "  —  required": "  —  обязательно",
    "Install and continue": "Установить и продолжить",
    "Installation error": "Ошибка установки",

    # --- integration dialog ------------------------------------------------
    "DocForge — Windows integration": "DocForge — интеграция с Windows",
    "Optional Explorer shortcuts. Entries are created for the current user only "
    "(HKCU), no administrator rights needed — untick to remove them.":
        "Необязательные ярлыки в Проводнике. Записи создаются только для текущего "
        "пользователя (HKCU), права администратора не нужны — снимите галочку, "
        "чтобы удалить.",
    "«{label}» entry in the context menu": "Пункт «{label}» в контекстном меню",
    "Right-click a file → the entry opens DocForge with it. "
    "Supported extensions: {n}.":
        "Правый клик по файлу → пункт открывает DocForge с этим файлом. "
        "Поддерживаемых расширений: {n}.",
    "DocForge shortcut in the SendTo menu": "Ярлык DocForge в меню «Отправить»",
    "Right-click → Send to → DocForge. Handier for several files at once: "
    "they open in one window as a single list.":
        "Правый клик → «Отправить» → DocForge. Для нескольких файлов сразу это "
        "удобнее: они открываются в одном окне одним списком.",
    "context-menu entry added": "пункт контекстного меню добавлен",
    "context-menu entry removed": "пункт контекстного меню удалён",
    "SendTo shortcut created": "ярлык «Отправить» создан",
    "SendTo shortcut removed": "ярлык «Отправить» удалён",
    "No changes.": "Изменений нет.",
    "Integration error": "Ошибка интеграции",

    # --- file dialogs ------------------------------------------------------
    "Supported files": "Поддерживаемые файлы",
    "Files with images": "Файлы с изображениями",
    "All files": "Все файлы",

    # --- errors (core/errors.py) -------------------------------------------
    "no write permission — the file may be open in another program ({e})":
        "нет прав на запись — возможно, файл открыт в другой программе ({e})",
    "file or folder not found ({e})": "файл или папка не найдены ({e})",
    "file system error ({e})": "ошибка файловой системы ({e})",
    "cancelled by the user": "отменено пользователем",

    # --- engine errors (core/pandoc.py) ------------------------------------
    "the Chromium engine is not installed — install it from the Components dialog":
        "движок Chromium не установлен — установите его в диалоге «Компоненты»",
    "PDF output needs a LaTeX engine — install MiKTeX (https://miktex.org), "
    "the app will find it automatically":
        "для вывода в PDF нужен LaTeX-движок — установите MiKTeX "
        "(https://miktex.org), приложение найдёт его автоматически",
    "MiKTeX seems to be missing LaTeX packages: open MiKTeX Console → Settings "
    "and enable 'Always install missing packages on-the-fly'":
        "похоже, MiKTeX не хватает LaTeX-пакетов: откройте MiKTeX Console → "
        "Settings и включите 'Always install missing packages on-the-fly'",

    # --- presets (core/presets.py) -----------------------------------------
    "Print-ready — PDF, 2 cm margins": "Для печати — PDF, поля 2 см",
    "Word document — with a table of contents": "Документ Word — с оглавлением",
    "For an LLM — Markdown": "Для LLM — Markdown",
    "A preset name cannot be empty": "Имя пресета не может быть пустым",
    "«{name}» is a built-in preset, choose another name":
        "«{name}» — встроенный пресет, выберите другое имя",
    "«{name}» is a built-in preset and cannot be deleted":
        "«{name}» — встроенный пресет, его нельзя удалить",

    # --- highlight styles / formats ----------------------------------------
    "Default": "По умолчанию",
    "No highlighting": "Без подсветки",
    "Plain Text": "Обычный текст",

    # --- installer progress ------------------------------------------------
    "Installing MarkItDown from pypi.org...": "Установка MarkItDown с pypi.org...",
    "Installing pypandoc from pypi.org...": "Установка pypandoc с pypi.org...",
    "Installing PyMuPDF from pypi.org...": "Установка PyMuPDF с pypi.org...",
    "Downloading Pandoc from github.com/jgm/pandoc (may take a minute)...":
        "Загрузка Pandoc с github.com/jgm/pandoc (может занять минуту)...",
    "Installing ffmpeg (imageio-ffmpeg) from pypi.org...":
        "Установка ffmpeg (imageio-ffmpeg) с pypi.org...",
    "Installing MiKTeX via winget (may take 5–10 minutes)...":
        "Установка MiKTeX через winget (может занять 5–10 минут)...",
    "Installing Playwright from pypi.org...": "Установка Playwright с pypi.org...",
    "Downloading Chromium (~150 MB, may take a few minutes)...":
        "Загрузка Chromium (~150 МБ, может занять несколько минут)...",
    "winget is unavailable. Install the component manually (id: {id}).":
        "winget недоступен. Установите компонент вручную (id: {id}).",

    # --- Explorer verb -----------------------------------------------------
    "Convert with DocForge": "Конвертировать через DocForge",

    # --- language switch ---------------------------------------------------
    "Language changed": "Язык изменён",
    "The interface language has been changed. Restart DocForge to apply it.":
        "Язык интерфейса изменён. Перезапустите DocForge, чтобы применить.",
}
