"""Confirmation dialogs shared by the tabs."""
import logging
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QWidget

from docforge.core.batch import Job
from docforge.core.paths import same_file, unique_path

log = logging.getLogger(__name__)


def resolve_output_conflict(parent: QWidget, output_path: str, input_path: str,
                            *, is_dir: bool = False) -> str | None:
    """Validate the output path before a conversion starts.

    Returns the final path (possibly changed), or None when the run must not
    proceed — the user cancelled, or the path collides with the input file.
    """
    # 1. The result must never clobber the source file
    if not is_dir and same_file(output_path, input_path):
        log.warning("Отказ: путь результата совпадает с исходным файлом (%s)", output_path)
        QMessageBox.critical(
            parent, "Совпадение путей",
            "Файл результата совпадает с исходным — конвертация уничтожила бы оригинал.\n\n"
            "Измените путь результата.",
        )
        return None

    p = Path(output_path)
    if not p.exists():
        return output_path
    # for a directory, only warn when it actually holds something
    if is_dir and p.is_dir() and not any(p.iterdir()):
        return output_path

    what = "Папка" if is_dir else "Файл"
    free = unique_path(output_path)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Результат уже существует")
    box.setText(f"{what} уже существует:\n{output_path}")
    box.setInformativeText(f"Сохранить рядом как «{free.name}» или перезаписать?")
    btn_keep = box.addButton(f"Сохранить как {free.name}", QMessageBox.ButtonRole.AcceptRole)
    btn_over = box.addButton("Перезаписать", QMessageBox.ButtonRole.DestructiveRole)
    btn_cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(btn_keep)
    box.exec()

    clicked = box.clickedButton()
    if clicked is btn_cancel:
        log.info("Конвертация отменена: результат уже существует (%s)", output_path)
        return None
    if clicked is btn_over:
        log.info("Перезапись существующего результата: %s", output_path)
        return output_path
    log.info("Результат сохраняется под свободным именем: %s", free)
    return str(free)


def _occupied(path: str, is_dir: bool) -> bool:
    """True if the target is in the way (an existing empty folder is not)."""
    p = Path(path)
    if not p.exists():
        return False
    if is_dir and p.is_dir():
        return any(p.iterdir())
    return True


def resolve_batch_conflicts(parent: QWidget, jobs: list[Job],
                            *, is_dir: bool = False) -> list[Job] | None:
    """Same checks as resolve_output_conflict, but asked once for the whole batch.

    Jobs whose result would overwrite their own source are dropped. If any
    results already exist, the user decides once for all of them. Returns the
    jobs to run, or None if the run was cancelled.
    """
    safe: list[Job] = []
    skipped_self = 0
    for job in jobs:
        if not is_dir and same_file(job.output_path, job.input_path):
            skipped_self += 1
            log.warning("Пропуск: результат совпал бы с исходным файлом (%s)", job.input_path)
            continue
        safe.append(job)

    if skipped_self:
        QMessageBox.warning(
            parent, "Совпадение путей",
            f"Пропущено файлов: {skipped_self} — результат совпал бы с исходным файлом.",
        )
    if not safe:
        return None

    existing = [j for j in safe if _occupied(j.output_path, is_dir)]
    if not existing:
        return safe

    what = "папок" if is_dir else "результатов"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Результаты уже существуют")
    box.setText(f"Уже существует {what}: {len(existing)} из {len(safe)}.")
    box.setInformativeText("Сохранить их рядом под свободными именами или перезаписать?")
    btn_keep = box.addButton("Сохранить рядом", QMessageBox.ButtonRole.AcceptRole)
    btn_over = box.addButton("Перезаписать", QMessageBox.ButtonRole.DestructiveRole)
    btn_cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(btn_keep)
    box.exec()

    clicked = box.clickedButton()
    if clicked is btn_cancel:
        log.info("Пакетная обработка отменена: %d результатов уже существуют", len(existing))
        return None
    if clicked is btn_over:
        log.info("Пакетная обработка: перезапись %d существующих результатов", len(existing))
        return safe

    # rename mode: reserve each name so two jobs can't claim the same one
    taken: set[str] = set()
    renamed: list[Job] = []
    for job in safe:
        target = unique_path(job.output_path, taken)
        taken.add(str(target))
        renamed.append(Job(job.input_path, str(target)))
    log.info("Пакетная обработка: %d результатов сохраняются под свободными именами", len(existing))
    return renamed
