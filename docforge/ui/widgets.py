from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QDialog, QSizePolicy,
)


class StatusLog(QWidget):
    """Однострочный статус + кнопка «Подробнее».

    В окне приложения видна только последняя строка (✓/✗/ℹ). Полный лог
    конвертации открывается по кнопке в отдельном небольшом окне — главное
    окно при этом не меняет размер.
    """

    def __init__(self) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._status = QLabel("")
        self._status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._status.setStyleSheet("color: #888; font-size: 11px;")

        self._btn = QPushButton("Подробнее")
        self._btn.setFixedWidth(90)
        self._btn.setToolTip("Открыть полный лог конвертации")
        self._btn.clicked.connect(self._show_details)

        row.addWidget(self._status, 1)
        row.addWidget(self._btn)

        self._lines: list[str] = []
        self._dialog: QDialog | None = None
        self._view: QTextEdit | None = None

    def append(self, text: str) -> None:
        self._lines.append(text)
        self._status.setText(text)
        if "✗" in text:
            self._status.setStyleSheet("color: #e06c6c; font-size: 11px;")
        elif "✓" in text:
            self._status.setStyleSheet("color: #5cb85c; font-size: 11px;")
        else:
            self._status.setStyleSheet("color: #aaa; font-size: 11px;")
        if self._view is not None:
            self._view.append(text)

    def _show_details(self) -> None:
        if self._dialog is None:
            self._dialog = QDialog(self)
            self._dialog.setWindowTitle("DocForge — лог конвертации")
            self._dialog.resize(560, 360)
            lay = QVBoxLayout(self._dialog)
            self._view = QTextEdit()
            self._view.setReadOnly(True)
            lay.addWidget(self._view)
        self._view.setPlainText("\n".join(self._lines))
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
