import os
import sys
import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication is instantiated in offscreen mode for testing."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app = QApplication(sys.argv)
    yield app


def test_main_window_instantiation(qapp):
    from src.gui.main_window import MainWindow
    window = MainWindow()
    assert window is not None
    assert window.windowTitle().startswith("gui-yt-dlp")
    window.close()
