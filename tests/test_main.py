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


def test_downloader_tab_options_building(qapp):
    from src.config import config_manager
    from src.gui.main_window import MainWindow

    window = MainWindow()
    tab = window.downloader_tab

    # Enable bypass throttling
    config_manager.set("bypass_throttling", True)

    # 1. Test "Best Quality" mode (mode_idx = 0) with default options
    tab.mode_combo.setCurrentIndex(0)
    opts = tab._build_ydl_opts()
    assert opts["format"] == "bestvideo+bestaudio/best"
    assert opts["extractor_args"]["youtube"]["player_client"] == ["web", "mweb", "android", "ios"]

    # 2. Test "Embed Thumbnail" checked
    tab.embed_thumb_check.setChecked(True)
    opts = tab._build_ydl_opts()
    assert opts["writethumbnail"] is True
    assert any(p.get("key") == "EmbedThumbnail" for p in opts.get("postprocessors", []))

    # 3. Test "Add Metadata" checked
    tab.add_metadata_check.setChecked(True)
    opts = tab._build_ydl_opts()
    assert any(p.get("key") == "FFmpegMetadata" for p in opts.get("postprocessors", []))

    # 4. Test "Audio Only (MP3)" mode (mode_idx = 2)
    tab.mode_combo.setCurrentIndex(2)
    opts = tab._build_ydl_opts()
    assert opts["format"] == "bestaudio/best"
    assert any(
        p.get("key") == "FFmpegExtractAudio" and p.get("preferredcodec") == "mp3"
        for p in opts.get("postprocessors", [])
    )

    window.close()
