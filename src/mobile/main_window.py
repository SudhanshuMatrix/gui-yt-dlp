from PySide6.QtWidgets import QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from ..config import config_manager
from ..constants import APP_NAME, APP_VERSION
from ..download_manager import download_manager
from ..utils.logger import get_logger
from .downloader_tab import DownloaderTab
from .library_tab import LibraryTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab
from .styles import MOBILE_QSS

logger = get_logger("mobile_main_window")

NAV_ITEMS = [("⬇", "Download"), ("☰", "Queue"), ("★", "Library"), ("⚙", "Settings")]


class MobileMainWindow(QWidget):
    """Touch-first main window: a QStackedWidget of screens with an Android-
    style bottom navigation bar, instead of the desktop app's title bar +
    sidebar (there's no window chrome to speak of on Android)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setStyleSheet(MOBILE_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.downloader_tab = DownloaderTab(self)
        self.queue_tab = QueueTab()
        self.library_tab = LibraryTab(self)
        self.settings_tab = SettingsTab(self)

        for page in (self.downloader_tab, self.queue_tab, self.library_tab, self.settings_tab):
            self.stack.addWidget(page)

        layout.addWidget(self.stack, 1)

        nav_bar = QWidget()
        nav_bar.setObjectName("navBar")
        nav_bar.setFixedHeight(64)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.nav_buttons: list[QPushButton] = []
        for idx, (icon_text, label) in enumerate(NAV_ITEMS):
            btn = QPushButton(f"{icon_text}\n{label}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, i=idx: self.switch_tab(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addWidget(nav_bar)

        self.switch_tab(0)

        download_manager.task_updated.connect(self._on_task_updated)

    def switch_tab(self, index: int):
        if not (0 <= index < self.stack.count()):
            return
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _on_task_updated(self, task_id: str, data: dict):
        # Placeholder hook for a future Android notification (e.g. via
        # plyer/jnius) when a download completes while the app is backgrounded.
        pass

    def closeEvent(self, event):
        config_manager.flush()
        download_manager.save_queue()
        event.accept()
