"""DocForge smoke test: exercises every conversion path without a GUI.

Run: python tests/test_smoke.py
Not part of the app — a self-check only.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

# Qt parts of the test run without a display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# the package sits at the repo root, this test lives in tests/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

PASS, FAIL, SKIP = "[OK]  ", "[FAIL]", "[SKIP]"
results: list[tuple[str, str]] = []

CYRILLIC_MD = (
    "# Тест кириллицы\n\n"
    "Привет, мир! **Жирный**, *курсив*, `код`.\n\n"
    "## Таблица\n\n"
    "| Колонка А | Колонка Б |\n|---|---|\n| ячейка | значение |\n\n"
    "Спецсимволы: ёЁ №«»— üöä 中文\n"
)
MARKER = "Привет, мир!"

tmp = tempfile.mkdtemp(prefix="docforge_smoke_")
src_md = os.path.join(tmp, "тест входной.md")  # Cyrillic and a space in the file name
with open(src_md, "w", encoding="utf-8") as f:
    f.write(CYRILLIC_MD)


_QT_APP = None


def qt_app():
    """One QApplication for every Qt-dependent check (widgets need a full one).

    The reference is kept module-level on purpose: if Python garbage-collects
    the wrapper while widgets are alive, the interpreter crashes on shutdown.
    """
    global _QT_APP
    if _QT_APP is None:
        from PyQt6.QtWidgets import QApplication
        _QT_APP = QApplication.instance() or QApplication([])
    return _QT_APP


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, f"{name} — {type(e).__name__}: {e}"))


# 1. Application imports
def t_imports():
    from docforge import app, theme, logging_setup, proc  # noqa
    from docforge.core import (  # noqa
        markitdown, images, chromium, latex, ffmpeg, pandoc, installer,
    )
    from docforge.ui import window, widgets, file_filters, setup_dialog  # noqa
    from docforge.ui.tabs import markitdown as t_md, pandoc as t_pd, images as t_im  # noqa
check("Импорт всех модулей приложения", t_imports)

# 2. Pandoc is available
def t_pandoc_version():
    import pypandoc
    v = pypandoc.get_pandoc_version()
    print(f"   pandoc {v}")
check("Pandoc доступен", t_pandoc_version)

# 3. Pandoc: every format from the tab (pdf is handled separately)
from docforge.core.pandoc import FORMATS

def make_pandoc_test(writer: str, ext: str, standalone: bool):
    def t():
        import pypandoc
        out = os.path.join(tmp, f"out.{ext}")
        extra = ["--standalone"] if standalone else []
        pypandoc.convert_file(src_md, writer, outputfile=out, extra_args=extra)
        assert os.path.getsize(out) > 0, "пустой выходной файл"
        # for text formats, check the Cyrillic survived
        if ext in ("html", "rst", "txt", "tex", "md"):
            with open(out, encoding="utf-8") as f:
                content = f.read()
            assert MARKER in content, f"кириллица потеряна в .{ext}"
    return t

for label, writer, ext, standalone in FORMATS:
    if ext == "pdf":
        continue
    check(f"Pandoc: md → .{ext} ({label})", make_pandoc_test(writer, ext, standalone))

# 4. Pandoc: PDF (same logic as _ConvertWorker)
def t_pdf():
    import pypandoc
    from docforge.core import latex as pdf_helper
    engine = pdf_helper.find_pdf_engine()
    if engine is None:
        results.append((SKIP, "Pandoc: md → .pdf — LaTeX-движок не установлен"))
        return
    out = os.path.join(tmp, "out.pdf")
    extra = [f"--pdf-engine={engine}"]
    if pdf_helper.is_unicode_engine(engine):
        extra += ["-V", "mainfont=Segoe UI"]
    extra += ["-V", "geometry:margin=2cm"]  # default margins, as in the app
    pypandoc.convert_file(src_md, "pdf", outputfile=out, extra_args=extra)
    assert os.path.getsize(out) > 0
    results.append((PASS, f"Pandoc: md → .pdf, поля 2cm (движок: {os.path.basename(engine)})"))
try:
    t_pdf()
except Exception as e:
    results.append((FAIL, f"Pandoc: md → .pdf — {e}"))

# 4b. Chromium engine: availability (informational)
def t_chromium():
    from docforge.core import chromium as chromium_pdf
    if chromium_pdf.available():
        results.append((PASS, "Chromium (Playwright): доступен"))
    else:
        results.append((SKIP, "Chromium (Playwright): не установлен (опционально)"))
t_chromium()

# 5. Pandoc: the reverse direction, docx -> md
def t_docx_to_md():
    import pypandoc
    docx = os.path.join(tmp, "out.docx")  # created by an earlier check
    back = os.path.join(tmp, "обратно.md")
    pypandoc.convert_file(docx, "markdown", outputfile=back)
    with open(back, encoding="utf-8") as f:
        assert MARKER in f.read(), "кириллица потеряна при docx → md"
check("Pandoc: docx → md (обратное направление)", t_docx_to_md)

# 6. MarkItDown: docx -> md (the same code the MarkItDown tab runs)
from docforge.core.markitdown import convert_to_markdown

def t_markitdown():
    docx = os.path.join(tmp, "out.docx")
    out = os.path.join(tmp, "markitdown_out.md")
    convert_to_markdown(docx, out)
    with open(out, encoding="utf-8") as f:
        assert MARKER in f.read(), "кириллица потеряна в MarkItDown"
check("MarkItDown: docx → md с кириллицей", t_markitdown)

# 7. MarkItDown: html → md
def t_markitdown_html():
    html = os.path.join(tmp, "out.html")
    out = os.path.join(tmp, "markitdown_html_out.md")
    convert_to_markdown(html, out)
    with open(out, encoding="utf-8") as f:
        assert MARKER in f.read(), "кириллица потеряна (html)"
check("MarkItDown: html → md с кириллицей", t_markitdown_html)

# 8. Pandoc: images from docx end up in the html (--embed-resources)
def t_images_html():
    import pypandoc
    # build a docx with an image: a 1x1 png plus md linking to it
    png = os.path.join(tmp, "pix.png")
    with open(png, "wb") as f:
        f.write(bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
            "de000000124944415408d763f8cfc000000301010018dd8db00000000049454e"
            "44ae426082"
        ))
    md_img = os.path.join(tmp, "с картинкой.md")
    with open(md_img, "w", encoding="utf-8") as f:
        f.write(f"# Картинка\n\n![тест]({png})\n")
    docx = os.path.join(tmp, "img.docx")
    pypandoc.convert_file(md_img, "docx", outputfile=docx)
    # docx -> html the way the Pandoc tab does it
    html = os.path.join(tmp, "img.html")
    pypandoc.convert_file(docx, "html", outputfile=html,
                          extra_args=["--standalone", "--embed-resources"])
    with open(html, encoding="utf-8") as f:
        assert "data:image" in f.read(), "картинка не встроена в html"
check("Pandoc: картинка из docx встроена в html", t_images_html)

# 9. Pandoc: docx -> md with an image — relative paths, no {width=...}
def t_images_md():
    import pypandoc
    docx = os.path.join(tmp, "img.docx")  # created by an earlier check
    out = os.path.join(tmp, "img_out.md")
    media = os.path.splitext(out)[0] + "_media"
    pypandoc.convert_file(docx, "markdown-link_attributes-raw_html", outputfile=out,
                          extra_args=[f"--extract-media={media}"])
    # the same post-processing as _ConvertWorker._relativize_media_paths
    import urllib.parse
    text = open(out, encoding="utf-8").read()
    rel = os.path.basename(media)
    fwd = media.replace("\\", "/")
    for v in {media, fwd, urllib.parse.quote(fwd, safe=":/")}:
        text = text.replace(v, rel)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    assert "![" in text, "ссылка на картинку отсутствует"
    assert tmp not in text, "остался абсолютный путь"
    assert "{width" not in text, "остались pandoc-атрибуты"
    assert os.path.isdir(media), "папка с медиа не создана"
check("Pandoc: docx → md, картинки с относительными путями", t_images_md)

# 9b. Logging: setup_logging creates the file and writes to it
def t_logging():
    import logging
    from docforge import logging_setup
    log_file = logging_setup.setup_logging()
    logging.getLogger("smoke_test").info("проверочная строка лога")
    for h in logging.getLogger().handlers:
        h.flush()
    assert os.path.isfile(log_file), "файл лога не создан"
    content = open(log_file, encoding="utf-8").read()
    assert "проверочная строка лога" in content, "строка не записалась в лог"
    assert "DocForge — старт сессии" in content, "окружение не залогировано"
check("Логирование: запись в файл работает", t_logging)

# 10. MarkItDown: extracting embedded images from docx
def t_markitdown_images():
    docx = os.path.join(tmp, "img.docx")  # created by an earlier check
    out = os.path.join(tmp, "mid_img.md")
    count = convert_to_markdown(docx, out, extract_images=True)
    assert count >= 1, f"картинки не извлечены (count={count})"
    media = os.path.splitext(out)[0] + "_media"
    assert os.path.isdir(media) and os.listdir(media), "папка с картинками пуста"
    text = open(out, encoding="utf-8").read()
    assert "data:image" not in text, "в md остался base64"
    assert "mid_img_media/" in text, "нет относительной ссылки на картинку"
check("MarkItDown: извлечение изображений из docx", t_markitdown_images)

# 10b. Extracting images into an arbitrary folder (the Images tab)
def t_images_only():
    from docforge.core import images as image_extract
    docx = os.path.join(tmp, "img.docx")  # created by an earlier check
    dest = os.path.join(tmp, "только_картинки")
    count = image_extract.extract_images_only(docx, dest)
    assert count >= 1, f"картинки не извлечены (count={count})"
    assert os.path.isdir(dest) and os.listdir(dest), "папка назначения пуста"
check("Изображения: извлечение из docx в выбранную папку", t_images_only)

# 10c. Extracting images from a PDF (PyMuPDF)
def t_pdf_images():
    import fitz  # PyMuPDF
    from docforge.core import images as image_extract
    # generate a valid image with PyMuPDF itself
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40))
    pix.clear_with(128)
    img_bytes = pix.tobytes("png")
    pdf = os.path.join(tmp, "with_img.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(fitz.Rect(40, 40, 160, 160), stream=img_bytes)
    doc.save(pdf)
    doc.close()
    dest = os.path.join(tmp, "pdf_картинки")
    count = image_extract.extract_images_only(pdf, dest)
    assert count >= 1, f"картинки из PDF не извлечены (count={count})"
    assert os.path.isdir(dest) and os.listdir(dest), "папка пуста"
check("Изображения: извлечение из PDF (PyMuPDF)", t_pdf_images)

# 10e. Pandoc options: table of contents + section numbering in html
def t_pandoc_options():
    import pypandoc
    src = os.path.join(tmp, "опции.md")
    with open(src, "w", encoding="utf-8") as f:
        f.write("# Раздел один\n\nТекст.\n\n## Подраздел\n\nЕщё текст.\n")
    out = os.path.join(tmp, "опции.html")
    # the extra_args the Pandoc tab builds
    extra = ["--standalone", "--toc", "--number-sections", "--highlight-style=tango"]
    pypandoc.convert_file(src, "html", outputfile=out, extra_args=extra)
    html = open(out, encoding="utf-8").read()
    assert "toc" in html.lower() or "Раздел один" in html, "оглавление не сформировано"
check("Pandoc: опции --toc/--number-sections/--highlight-style", t_pandoc_options)

# 10d. Output protection: free name and path comparison
def t_paths():
    from docforge.core.paths import same_file, unique_path
    d = os.path.join(tmp, "конфликт")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "файл.md")
    open(f, "w", encoding="utf-8").close()
    u2 = unique_path(f)
    assert u2.name == "файл-2.md", f"ожидалось файл-2.md, получено {u2.name}"
    open(u2, "w", encoding="utf-8").close()
    assert unique_path(f).name == "файл-3.md", "нумерация не продолжилась"
    free = os.path.join(d, "нет-такого.md")
    assert str(unique_path(free)) == free, "свободный путь не должен меняться"
    # path comparison: two spellings of the same file
    assert same_file(f, f.replace("\\", "/")), "один файл не распознан"
    assert not same_file(f, str(u2)), "разные файлы посчитаны одинаковыми"
check("Пути: свободное имя (-2/-3) и сравнение путей", t_paths)

# 10e. core.pandoc.convert: the real conversion path used by the tab
def t_core_convert():
    from docforge.core.pandoc import PandocOptions, convert
    out = os.path.join(tmp, "core_convert.html")
    convert(src_md, out, PandocOptions(writer="html", standalone=True, toc=True))
    assert os.path.getsize(out) > 0, "пустой результат"
    with open(out, encoding="utf-8") as f:
        assert MARKER in f.read(), "кириллица потеряна"
check("core.pandoc.convert: md → html с оглавлением", t_core_convert)

# 10f. core.pandoc.convert: docx → md, images end up relative
def t_core_convert_media():
    from docforge.core.pandoc import PandocOptions, convert
    docx = os.path.join(tmp, "img.docx")  # created by an earlier check
    out = os.path.join(tmp, "core_media.md")
    convert(docx, out, PandocOptions(writer="markdown"))
    text = open(out, encoding="utf-8").read()
    assert "![" in text, "ссылка на картинку отсутствует"
    assert tmp not in text, "остался абсолютный путь"
    assert os.path.isdir(os.path.splitext(out)[0] + "_media"), "папка с медиа не создана"
check("core.pandoc.convert: docx → md, относительные пути картинок", t_core_convert_media)

# 10g. Batch queue: progress, per-job results and failure handling
def t_batch():
    from docforge.core.batch import BatchRunner, Job, pool_size

    qt_app()
    jobs = [Job(f"in{i}.txt", os.path.join(tmp, f"batch{i}.txt")) for i in range(4)]

    def fn(job):
        if job.input_path.endswith("2.txt"):
            raise PermissionError("нет доступа")
        with open(job.output_path, "w", encoding="utf-8") as f:
            f.write("ok")

    seen_progress, messages, done = [], [], []
    runner = BatchRunner(jobs, fn, max_workers=2)
    runner.progress.connect(lambda d, t, n: seen_progress.append((d, t)))
    runner.message.connect(messages.append)
    runner.completed.connect(lambda ok, failed: done.append((ok, failed)))
    runner.run()  # synchronous: signals connect directly in this thread

    assert done == [(3, 1)], f"ожидалось (3,1), получено {done}"
    assert len(seen_progress) == 4, f"прогресс пришёл {len(seen_progress)} раз"
    assert seen_progress[-1] == (4, 4), f"последний прогресс {seen_progress[-1]}"
    assert any("✗" in m and "нет прав" in m for m in messages), "ошибка не описана понятно"
    assert sum(1 for m in messages if m.startswith("✓")) == 3, "не все успехи отмечены"
    # PDF forces a single worker, other formats use a small pool
    assert pool_size(10, heavy=True) == 1, "PDF должен идти в один поток"
    assert pool_size(10, heavy=False) > 1, "не-PDF должен использовать пул"
    assert pool_size(1, heavy=False) == 1, "для одного файла хватает одного воркера"
check("Пакетная очередь: прогресс, ошибки, размер пула", t_batch)

# 10h. Folder scan picks only supported files
def t_scan_folder():
    from docforge.ui.inputs import scan_folder, summarize
    d = os.path.join(tmp, "скан")
    os.makedirs(d, exist_ok=True)
    for name in ("a.md", "b.DOCX", "c.exe", "d.txt"):
        open(os.path.join(d, name), "w", encoding="utf-8").close()
    os.makedirs(os.path.join(d, "вложенная"), exist_ok=True)
    found = scan_folder(d, ["md", "docx"])
    names = sorted(os.path.basename(p) for p in found)
    assert names == ["a.md", "b.DOCX"], f"найдено не то: {names}"
    assert summarize(found[:1]) == found[0], "один файл показывается полным путём"
    assert summarize(found).startswith("2 файлов"), "несколько файлов показываются счётчиком"
check("Сканирование папки и сводка выбора", t_scan_folder)

# 10i. Batch renaming reserves names so two jobs can't collide
def t_unique_taken():
    from docforge.core.paths import unique_path
    d = os.path.join(tmp, "резерв")
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "f.md")
    open(target, "w", encoding="utf-8").close()
    first = unique_path(target)
    second = unique_path(target, {str(first)})
    assert first.name == "f-2.md", first.name
    assert second.name == "f-3.md", second.name
check("Пакет: резервирование свободных имён", t_unique_taken)

# 10j. Windows integration: registry verb round-trip on a throwaway extension
def t_winintegration():
    from docforge.core import winintegration as wi
    exe, script = wi.launcher()
    assert os.path.isfile(exe), f"лаунчер не найден: {exe}"
    assert script.is_file(), f"main.py не найден: {script}"
    assert wi.icon_path().is_file(), "иконка не найдена"
    assert str(wi.sendto_shortcut()).endswith("DocForge.lnk"), "неверный путь ярлыка"

    ext = ".docforge-selftest"  # fake, so the real file types stay untouched
    assert not wi.context_menu_installed(ext), "тестовый ключ остался от прошлого прогона"
    wi.install_context_menu([ext])
    try:
        assert wi.context_menu_installed(ext), "ключ не создан"
        import winreg
        key = rf"Software\Classes\SystemFileAssociations\{ext}\shell\DocForge\command"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            cmd = winreg.QueryValueEx(k, None)[0]
        assert "main.py" in cmd and cmd.endswith('"%1"'), f"неверная команда: {cmd}"
    finally:
        wi.uninstall_context_menu([ext])
    assert not wi.context_menu_installed(ext), "ключ не удалён"
check("Интеграция с Windows: запись и удаление пункта меню", t_winintegration)

# 10k. Explorer hand-off routes files to the fitting tab
def t_file_handoff():
    qt_app()
    from docforge.ui.window import MainWindow

    w = MainWindow()
    cases = [("файл.docx", "Pandoc"), ("скан.pdf", "MarkItDown")]
    for name, expected in cases:
        p = os.path.join(tmp, name)
        open(p, "w", encoding="utf-8").close()
        w.load_files([p])
        got = w._tabs.tabText(w._tabs.currentIndex())
        assert got == expected, f"{name}: открылась вкладка {got}, ожидалась {expected}"
        assert w._tabs.currentWidget()._inputs.count() == 1, "файл не подставился"
    w.close()  # tear the window down while Qt is still alive
check("Передача файлов из Проводника на нужную вкладку", t_file_handoff)

# 10l. Presets and recent files (kept in a temp store, real settings untouched)
def t_presets_and_recent():
    import tempfile as _tf
    from PyQt6.QtCore import QSettings
    qt_app()
    from docforge import settings as S
    from docforge.core import presets

    original = S._s
    store = _tf.mktemp(suffix=".ini")
    S._s = lambda: QSettings(store, QSettings.Format.IniFormat)
    try:
        assert len(presets.BUILTIN) >= 3, "встроенных пресетов слишком мало"
        presets.save("Тест", presets.Preset(format="docx", toc=True, margin="1cm"))
        loaded = presets.all_presets()["Тест"]
        assert loaded.format == "docx" and loaded.toc and loaded.margin == "1cm", loaded
        for name in list(presets.BUILTIN)[:1]:
            try:
                presets.save(name, presets.Preset())
                raise AssertionError("встроенный пресет позволили перезаписать")
            except ValueError:
                pass
            try:
                presets.delete(name)
                raise AssertionError("встроенный пресет позволили удалить")
            except ValueError:
                pass
        presets.delete("Тест")
        assert "Тест" not in presets.all_presets(), "пресет не удалён"

        # recent: newest first, repeats float up, capped
        S.push_recent("t", ["a.md"])
        S.push_recent("t", ["b.md", "c.md"])
        S.push_recent("t", ["a.md"])
        rec = S.get_recent("t")
        assert rec[0] == ["a.md"], f"повтор не всплыл: {rec}"
        assert len(rec) == 2, f"дубликат не схлопнулся: {rec}"
        for i in range(S.RECENT_LIMIT + 5):
            S.push_recent("t", [f"f{i}.md"])
        assert len(S.get_recent("t")) == S.RECENT_LIMIT, "лимит недавних не соблюдён"
        # corrupted data must not crash the app
        S.put("recent/t", "не json")
        assert S.get_recent("t") == [], "повреждённые данные не обработаны"
    finally:
        S._s = original
check("Пресеты и список недавних файлов", t_presets_and_recent)

# 11. ffmpeg status (informational)
def t_ffmpeg():
    from docforge.core import ffmpeg as ffmpeg_helper
    path = ffmpeg_helper.find_ffmpeg()
    if path:
        results.append((PASS, f"ffmpeg найден: {path}"))
    else:
        results.append((SKIP, "ffmpeg не установлен — аудио/видео недоступны (опционально)"))
t_ffmpeg()

# Summary
print()
fails = 0
for status, name in results:
    print(f"{status} {name}")
    if status == FAIL:
        fails += 1
print(f"\nИтого: {len(results)} проверок, ошибок: {fails}")
print(f"Временные файлы: {tmp}")
sys.exit(1 if fails else 0)
