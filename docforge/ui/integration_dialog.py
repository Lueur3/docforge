"""Dialog for the optional Windows shell integration."""
import logging

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from docforge.core import winintegration as wi
from docforge.ui import file_filters

log = logging.getLogger(__name__)

# Extensions offered in the Explorer context menu: everything either converter
# can read, without duplicates, as ".ext"
MENU_EXTS = sorted(
    {f".{e}" for e in file_filters.PANDOC_EXTS + file_filters.MARKITDOWN_EXTS}
)


class IntegrationDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("DocForge — интеграция с Windows")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        intro = QLabel(
            "Необязательные ярлыки в Проводнике. Записи создаются только для текущего "
            "пользователя (HKCU), права администратора не нужны — снимите галочку, "
            "чтобы удалить."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(6)

        self._menu_chk = QCheckBox(f"Пункт «{wi.VERB_LABEL}» в контекстном меню")
        self._menu_chk.setChecked(self._menu_state())
        layout.addWidget(self._menu_chk)
        layout.addWidget(self._hint(
            f"Правый клик по файлу → пункт открывает DocForge с этим файлом. "
            f"Поддерживаемых расширений: {len(MENU_EXTS)}."
        ))

        self._sendto_chk = QCheckBox("Ярлык DocForge в меню «Отправить»")
        self._sendto_chk.setChecked(wi.sendto_installed())
        layout.addWidget(self._sendto_chk)
        layout.addWidget(self._hint(
            "Правый клик → «Отправить» → DocForge. Для нескольких файлов сразу это "
            "удобнее: они открываются в одном окне одним списком."
        ))

        layout.addSpacing(8)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        apply_btn = QPushButton("Применить")
        apply_btn.setFixedHeight(32)
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)

    def _hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px;")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _menu_state() -> bool:
        """Considered installed when the verb is registered for any extension."""
        return any(wi.context_menu_installed(ext) for ext in MENU_EXTS)

    def _apply(self) -> None:
        changes: list[str] = []
        try:
            want_menu = self._menu_chk.isChecked()
            if want_menu != self._menu_state():
                if want_menu:
                    wi.install_context_menu(MENU_EXTS)
                    changes.append("пункт контекстного меню добавлен")
                else:
                    wi.uninstall_context_menu(MENU_EXTS)
                    changes.append("пункт контекстного меню удалён")

            want_sendto = self._sendto_chk.isChecked()
            if want_sendto != wi.sendto_installed():
                if want_sendto:
                    wi.install_sendto()
                    changes.append("ярлык «Отправить» создан")
                else:
                    wi.uninstall_sendto()
                    changes.append("ярлык «Отправить» удалён")
        except Exception as e:
            log.exception("Интеграция: не удалось применить настройки")
            QMessageBox.warning(self, "Ошибка интеграции", str(e))
            return

        if changes:
            self._status.setText("✓ " + ", ".join(changes))
            self._status.setStyleSheet("color: #5cb85c; font-size: 11px;")
        else:
            self._status.setText("Изменений нет.")
            self._status.setStyleSheet("color: #888; font-size: 11px;")


def open_integration_dialog(parent: QWidget | None = None) -> None:
    log.info("Открытие диалога интеграции")
    IntegrationDialog(parent).exec()
