import platform
import sys
import logging
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.agri_analyzer import __app_name__, __version__
from src.agri_analyzer.utils.logging_config import configure_logging, log_file_path


logger = logging.getLogger(__name__)


def preferred_font_family() -> str:
    system = platform.system()
    if system == "Windows":
        return "Microsoft YaHei"
    if system == "Darwin":
        return "PingFang SC"
    return QApplication.font().family()


def main() -> int:
    configure_logging()
    logger.info(
        "Starting %s %s; platform=%s; python=%s; frozen=%s; cwd=%s; meipass=%s; log_file=%s",
        __app_name__,
        __version__,
        platform.platform(),
        sys.version.replace("\n", " "),
        bool(getattr(sys, "frozen", False)),
        Path.cwd(),
        getattr(sys, "_MEIPASS", ""),
        log_file_path(),
    )
    app = QApplication(sys.argv)
    app.setFont(QFont(preferred_font_family(), 10))
    logger.debug("Importing main window after logging is configured.")
    from src.agri_analyzer.ui.main_window import MainWindow

    logger.debug("Creating main window.")
    window = MainWindow()
    window.show()
    logger.info("Main window shown.")
    return app.exec()
