import sys
import os
from os import path

# Compatibility check to allow running this script directly
if __name__ == "__main__" and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    __package__ = "src"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt
from .gui.main_window import MainWindow
from .utils.logger import get_logger

logger = get_logger("main")

def main():
    # Configure high DPI scaling
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("gui-yt-dlp")
    app.setDesktopFileName("gui-yt-dlp")
    app.setOrganizationName("yt-dlp Flow Team")
    app.setApplicationVersion("1.0.0")
    
    from PySide6.QtGui import QIcon
    logo_path = os.path.join(os.path.dirname(__file__), "gui", "assets", "logo.png")
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    # Create the main window
    window = MainWindow()
    window.show()
    
    logger.info("Application started.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
