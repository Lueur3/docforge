from PyQt6.QtWidgets import QMainWindow, QTabWidget

from tab_markitdown import MarkItDownTab
from tab_pandoc import PandocTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocForge")
        self.setMinimumSize(600, 400)
        self.resize(600, 400)

        tabs = QTabWidget()
        tabs.addTab(MarkItDownTab(), "MarkItDown")
        tabs.addTab(PandocTab(), "Pandoc")
        self.setCentralWidget(tabs)
