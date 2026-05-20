import platform
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.agri_analyzer.ui.main_window import MainWindow


def preferred_font_family() -> str:
    system = platform.system()
    if system == "Windows":
        return "Microsoft YaHei"
    if system == "Darwin":
        return "PingFang SC"
    return QApplication.font().family()


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont(preferred_font_family(), 10))
    window = MainWindow()
    window.show()
    return app.exec()
