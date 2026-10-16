import sys
from pathlib import Path

# Compatibility check to allow running this script directly
if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    __package__ = "src"

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from .config import config_manager
from .constants import APP_NAME, APP_VERSION
from .mobile.main_window import MobileMainWindow
from .utils.logger import get_logger

logger = get_logger("mobile_main")


def main():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("yt-dlp Flow Team")
    app.setApplicationVersion(APP_VERSION)

    window = MobileMainWindow()
    # showMaximized() rather than show(): Android runs the app fullscreen
    # regardless, and this also behaves sensibly if ever run windowed on desktop.
    window.showMaximized()

    logger.info(f"{APP_NAME} v{APP_VERSION} (mobile) started.")
    ret_code = app.exec()

    config_manager.flush()
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
