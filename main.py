import sys
import os

# Форсируем UTF-8 до любых других импортов
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

from deps import ensure_dependencies
from window import MainWindow


def _apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(28, 28, 28))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(212, 212, 212))
    p.setColor(QPalette.ColorRole.Base,            QColor(18, 18, 18))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(38, 38, 38))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(42, 42, 42))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(212, 212, 212))
    p.setColor(QPalette.ColorRole.Text,            QColor(212, 212, 212))
    p.setColor(QPalette.ColorRole.Button,          QColor(45, 45, 45))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(212, 212, 212))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(100, 100, 100))

    # Отключённые элементы
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(90, 90, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(90, 90, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(90, 90, 90))

    app.setPalette(p)

    app.setStyleSheet("""
        QTabWidget::pane  { border: 1px solid #3a3a3a; }
        QTabBar::tab      { padding: 6px 18px; background: #2a2a2a; }
        QTabBar::tab:selected   { background: #3a3a3a; color: #ffffff; }
        QTabBar::tab:hover      { background: #363636; }
        QLineEdit  { padding: 4px 6px; border: 1px solid #3a3a3a; border-radius: 3px; }
        QComboBox  { padding: 4px 6px; border: 1px solid #3a3a3a; border-radius: 3px; }
        QTextEdit  { border: 1px solid #3a3a3a; border-radius: 3px; }
        QPushButton {
            padding: 4px 12px;
            border: 1px solid #3a3a3a;
            border-radius: 3px;
            background: #3a3a3a;
        }
        QPushButton:hover    { background: #484848; }
        QPushButton:pressed  { background: #2a2a2a; }
        QPushButton:disabled { background: #2a2a2a; color: #666; }
        QPushButton#btn_convert {
            background: #1a6fba;
            border-color: #1a6fba;
            color: #fff;
            font-weight: bold;
        }
        QPushButton#btn_convert:hover    { background: #2a7fca; }
        QPushButton#btn_convert:pressed  { background: #1060a0; }
        QPushButton#btn_convert:disabled { background: #1a3a5a; color: #667; }
    """)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DocForge")

    _apply_dark_theme(app)
    ensure_dependencies(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
