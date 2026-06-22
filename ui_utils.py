from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QSizePolicy,
)


class LogPanel(QWidget):
    """Сворачиваемая панель лога: кнопка-переключатель + текстовое поле.

    По умолчанию лог скрыт. При появлении ошибки (строка с «✗») разворачивается
    автоматически, чтобы пользователь её увидел.
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._btn = QPushButton("Показать лог ▸")
        self._btn.setCheckable(True)
        self._btn.setFixedHeight(24)
        self._btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._btn)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._log.hide()
        layout.addWidget(self._log)

    def _on_toggle(self, checked: bool) -> None:
        self._set_open(checked)

    def _set_open(self, opened: bool) -> None:
        self._log.setVisible(opened)
        self._btn.setChecked(opened)
        self._btn.setText("Скрыть лог ▾" if opened else "Показать лог ▸")

    def append(self, text: str) -> None:
        self._log.append(text)
        if "✗" in text and not self._log.isVisible():
            self._set_open(True)
