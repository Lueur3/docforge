"""Dialog for the optional Windows shell integration."""
import logging

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from docforge.core import winintegration as wi
from docforge.i18n import tr
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
        self.setWindowTitle(tr("DocForge — Windows integration"))
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        intro = QLabel(
            tr("Optional Explorer shortcuts. Entries are created for the current user "
               "only (HKCU), no administrator rights needed — untick to remove them.")
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(6)

        self._menu_chk = QCheckBox(tr("«{label}» entry in the context menu").format(label=wi.verb_label()))
        self._menu_chk.setChecked(self._menu_state())
        layout.addWidget(self._menu_chk)
        layout.addWidget(self._hint(
            tr("Right-click a file → the entry opens DocForge with it. "
               "Supported extensions: {n}.").format(n=len(MENU_EXTS))
        ))

        self._sendto_chk = QCheckBox(tr("DocForge shortcut in the SendTo menu"))
        self._sendto_chk.setChecked(wi.sendto_installed())
        layout.addWidget(self._sendto_chk)
        layout.addWidget(self._hint(
            tr("Right-click → Send to → DocForge. Handier for several files at once: "
               "they open in one window as a single list.")
        ))

        layout.addSpacing(8)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        apply_btn = QPushButton(tr("Apply"))
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
                    changes.append(tr("context-menu entry added"))
                else:
                    wi.uninstall_context_menu(MENU_EXTS)
                    changes.append(tr("context-menu entry removed"))

            want_sendto = self._sendto_chk.isChecked()
            if want_sendto != wi.sendto_installed():
                if want_sendto:
                    wi.install_sendto()
                    changes.append(tr("SendTo shortcut created"))
                else:
                    wi.uninstall_sendto()
                    changes.append(tr("SendTo shortcut removed"))
        except Exception as e:
            log.exception("Интеграция: не удалось применить настройки")
            QMessageBox.warning(self, tr("Integration error"), str(e))
            return

        if changes:
            self._status.setText("✓ " + ", ".join(changes))
            self._status.setStyleSheet("color: #5cb85c; font-size: 11px;")
        else:
            self._status.setText(tr("No changes."))
            self._status.setStyleSheet("color: #888; font-size: 11px;")


def open_integration_dialog(parent: QWidget | None = None) -> None:
    log.info("Открытие диалога интеграции")
    IntegrationDialog(parent).exec()
