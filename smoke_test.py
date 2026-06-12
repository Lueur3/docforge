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

# 4. Pandoc: PDF (требует LaTeX — допустимо отсутствие)
def t_pdf():
    import pypandoc, shutil
    if not (shutil.which("pdflatex") or shutil.which("xelatex") or shutil.which("tectonic")):
        results.append((SKIP, "Pandoc: md → .pdf — LaTeX-движок не установлен (ожидаемо)"))
        return
    out = os.path.join(tmp, "out.pdf")
    pypandoc.convert_file(src_md, "pdf", outputfile=out)
    assert os.path.getsize(out) > 0
try:
    t_pdf()
    if not any("pdf" in r[1] for r in results):
        results.append((PASS, "Pandoc: md → .pdf"))
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

# 8. ffmpeg-статус (информационно)
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
