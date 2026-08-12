import os
import sys
from pathlib import Path

# Compatibility check to allow running this script directly
if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    __package__ = "src"

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from .constants import APP_NAME, APP_VERSION, get_asset_path
from .gui.main_window import MainWindow
from .config import config_manager
from .utils.logger import get_logger

logger = get_logger("main")


def main():
    # Configure high DPI scaling
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_NAME)
    app.setOrganizationName("yt-dlp Flow Team")
    app.setApplicationVersion(APP_VERSION)

    logo_path = get_asset_path("logo.jpeg")
    if logo_path and os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    # Create the main window
    window = MainWindow()
    window.show()

    logger.info(f"{APP_NAME} v{APP_VERSION} started.")
    ret_code = app.exec()
    
    # Save any pending config changes on exit
    config_manager.flush()
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
