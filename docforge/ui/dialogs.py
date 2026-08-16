"""Confirmation dialogs shared by the tabs."""
import logging
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QWidget

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
