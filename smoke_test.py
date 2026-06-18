"""Smoke-тест DocForge: проверяет все пути конвертации без GUI.

Запуск: python smoke_test.py
Не входит в приложение — только для проверки работоспособности.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

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
src_md = os.path.join(tmp, "тест входной.md")  # кириллица и пробел в имени файла
with open(src_md, "w", encoding="utf-8") as f:
    f.write(CYRILLIC_MD)


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, f"{name} — {type(e).__name__}: {e}"))


# 1. Импорты приложения
def t_imports():
    import deps, ffmpeg_helper, window, tab_markitdown, tab_pandoc  # noqa
check("Импорт всех модулей приложения", t_imports)

# 2. Pandoc установлен
def t_pandoc_version():
    import pypandoc
    v = pypandoc.get_pandoc_version()
    print(f"   pandoc {v}")
check("Pandoc доступен", t_pandoc_version)

# 3. Pandoc: все форматы из вкладки (кроме pdf — отдельно)
from tab_pandoc import FORMATS

def make_pandoc_test(writer: str, ext: str, standalone: bool):
    def t():
        import pypandoc
        out = os.path.join(tmp, f"out.{ext}")
        extra = ["--standalone"] if standalone else []
        pypandoc.convert_file(src_md, writer, outputfile=out, extra_args=extra)
        assert os.path.getsize(out) > 0, "пустой выходной файл"
        # для текстовых форматов проверяем что кириллица уцелела
        if ext in ("html", "rst", "txt", "tex", "md"):
            with open(out, encoding="utf-8") as f:
                content = f.read()
            assert MARKER in content, f"кириллица потеряна в .{ext}"
    return t

for label, writer, ext, standalone in FORMATS:
    if ext == "pdf":
        continue
    check(f"Pandoc: md → .{ext} ({label})", make_pandoc_test(writer, ext, standalone))

# 4. Pandoc: PDF (та же логика, что в _ConvertWorker)
def t_pdf():
    import pypandoc
    import pdf_helper
    engine = pdf_helper.find_pdf_engine()
    if engine is None:
        results.append((SKIP, "Pandoc: md → .pdf — LaTeX-движок не установлен"))
        return
    out = os.path.join(tmp, "out.pdf")
    extra = [f"--pdf-engine={engine}"]
    if pdf_helper.is_unicode_engine(engine):
        extra += ["-V", "mainfont=Segoe UI"]
    pypandoc.convert_file(src_md, "pdf", outputfile=out, extra_args=extra)
    assert os.path.getsize(out) > 0
    results.append((PASS, f"Pandoc: md → .pdf (движок: {os.path.basename(engine)})"))
try:
    t_pdf()
except Exception as e:
    results.append((FAIL, f"Pandoc: md → .pdf — {e}"))

# 5. Pandoc: обратное направление docx → md
def t_docx_to_md():
    import pypandoc
    docx = os.path.join(tmp, "out.docx")  # создан тестом выше
    back = os.path.join(tmp, "обратно.md")
    pypandoc.convert_file(docx, "markdown", outputfile=back)
    with open(back, encoding="utf-8") as f:
        assert MARKER in f.read(), "кириллица потеряна при docx → md"
check("Pandoc: docx → md (обратное направление)", t_docx_to_md)

# 6. MarkItDown: docx → md (тот же код, что выполняет вкладка MarkItDown)
from tab_markitdown import convert_to_markdown

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

# 8. Pandoc: картинки из docx попадают в html (--embed-resources)
def t_images_html():
    import pypandoc
    # делаем docx с картинкой: png 1x1 + md со ссылкой на неё
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
    # docx → html как делает вкладка Pandoc
    html = os.path.join(tmp, "img.html")
    pypandoc.convert_file(docx, "html", outputfile=html,
                          extra_args=["--standalone", "--embed-resources"])
    with open(html, encoding="utf-8") as f:
        assert "data:image" in f.read(), "картинка не встроена в html"
check("Pandoc: картинка из docx встроена в html", t_images_html)

# 9. Pandoc: docx → md с картинкой — пути относительные, без {width=...}
def t_images_md():
    import pypandoc
    docx = os.path.join(tmp, "img.docx")  # создан тестом выше
    out = os.path.join(tmp, "img_out.md")
    media = os.path.splitext(out)[0] + "_media"
    pypandoc.convert_file(docx, "markdown-link_attributes-raw_html", outputfile=out,
                          extra_args=[f"--extract-media={media}"])
    # та же пост-обработка, что в _ConvertWorker._relativize_media_paths
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

# 9b. Логирование: setup_logging создаёт файл и пишет в него
def t_logging():
    import logging
    import logging_setup
    log_file = logging_setup.setup_logging()
    logging.getLogger("smoke_test").info("проверочная строка лога")
    for h in logging.getLogger().handlers:
        h.flush()
    assert os.path.isfile(log_file), "файл лога не создан"
    content = open(log_file, encoding="utf-8").read()
    assert "проверочная строка лога" in content, "строка не записалась в лог"
    assert "DocForge — старт сессии" in content, "окружение не залогировано"
check("Логирование: запись в файл работает", t_logging)

# 10. MarkItDown: извлечение встроенных изображений из docx
def t_markitdown_images():
    docx = os.path.join(tmp, "img.docx")  # создан тестом выше
    out = os.path.join(tmp, "mid_img.md")
    count = convert_to_markdown(docx, out, extract_images=True)
    assert count >= 1, f"картинки не извлечены (count={count})"
    media = os.path.splitext(out)[0] + "_media"
    assert os.path.isdir(media) and os.listdir(media), "папка с картинками пуста"
    text = open(out, encoding="utf-8").read()
    assert "data:image" not in text, "в md остался base64"
    assert "mid_img_media/" in text, "нет относительной ссылки на картинку"
check("MarkItDown: извлечение изображений из docx", t_markitdown_images)

# 11. ffmpeg-статус (информационно)
def t_ffmpeg():
    import ffmpeg_helper
    path = ffmpeg_helper.find_ffmpeg()
    if path:
        results.append((PASS, f"ffmpeg найден: {path}"))
    else:
        results.append((SKIP, "ffmpeg не установлен — аудио/видео недоступны (опционально)"))
t_ffmpeg()

# Итог
print()
fails = 0
for status, name in results:
    print(f"{status} {name}")
    if status == FAIL:
        fails += 1
print(f"\nИтого: {len(results)} проверок, ошибок: {fails}")
print(f"Временные файлы: {tmp}")
sys.exit(1 if fails else 0)
