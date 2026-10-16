import os
import sys

from PySide6.QtCore import QEvent, Slot
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QSystemTrayIcon
from qfluentwidgets import (
    Action,
    FluentIcon,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    RoundMenu,
)

from ..config import config_manager
from ..constants import APP_NAME, APP_VERSION, get_asset_path
from ..download_manager import download_manager
from ..utils.ffmpeg_check import find_ffmpeg
from ..utils.ffmpeg_downloader import FfmpegDownloadWorker, get_managed_ffmpeg_bin
from ..utils.logger import get_logger
from ..utils.network_monitor import NetworkMonitor
from .downloader_tab import DownloaderTab
from .library_tab import LibraryTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab, YtdlUpdateWorker
from .themes import apply_saved_appearance

logger = get_logger("main_window")


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — yt-dlp Desktop Frontend")
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)

        apply_saved_appearance(config_manager)

        logo_path = get_asset_path("logo.jpeg")
        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._offline_bar: InfoBar | None = None

        self._init_ui()
        self._init_shortcuts()
        self._init_system_tray()

        # Trigger background auto-update if enabled
        if config_manager.get("auto_update", True) and not getattr(sys, "frozen", False):
            self._trigger_silent_update()

        # Start network monitor
        self.network_monitor = NetworkMonitor()
        self.network_monitor.status_changed.connect(self._on_network_status_changed)
        self.network_monitor.start()

        # Connect task completion signal to system notification
        download_manager.task_updated.connect(self._on_task_updated)

        # Check for FFmpeg and silently download if missing
        self._check_and_download_ffmpeg()

    def _init_ui(self):
        self.downloader_tab = DownloaderTab(self)
        self.queue_tab = QueueTab()
        self.library_tab = LibraryTab(self)
        self.settings_tab = SettingsTab(self)

        self.downloader_tab.setObjectName("downloaderInterface")
        self.queue_tab.setObjectName("queueInterface")
        self.library_tab.setObjectName("libraryInterface")
        self.settings_tab.setObjectName("settingsInterface")

        self.addSubInterface(self.downloader_tab, FluentIcon.CLOUD_DOWNLOAD, "Downloader")
        self.addSubInterface(self.queue_tab, FluentIcon.SYNC, "Queue")
        self.addSubInterface(self.library_tab, FluentIcon.LIBRARY_FILL, "Library")
        self.addSubInterface(
            self.settings_tab, FluentIcon.SETTING, "Settings", NavigationItemPosition.BOTTOM
        )

        self.navigationInterface.setExpandWidth(220)

    def _init_shortcuts(self):
        """Set up global keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.switch_tab(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.switch_tab(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.switch_tab(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.switch_tab(3))
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: download_manager.pause_all())
        QShortcut(QKeySequence("Ctrl+R"), self, lambda: self.library_tab.refresh_library())

    def _init_system_tray(self):
        """Set up system tray icon and menu."""
        logo_path = get_asset_path("logo.jpeg")
        if (
            not logo_path
            or not os.path.exists(logo_path)
            or not QSystemTrayIcon.isSystemTrayAvailable()
        ):
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(QIcon(logo_path), self)
        self.tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        tray_menu = RoundMenu(parent=self)
        show_action = Action(FluentIcon.VIEW, "Show Application", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)

        pause_action = Action(FluentIcon.PAUSE, "Pause All Downloads", self)
        pause_action.triggered.connect(lambda: download_manager.pause_all())
        tray_menu.addAction(pause_action)

        resume_action = Action(FluentIcon.PLAY, "Resume All Downloads", self)
        resume_action.triggered.connect(lambda: download_manager.resume_all())
        tray_menu.addAction(resume_action)

        tray_menu.addSeparator()
        quit_action = Action(FluentIcon.CLOSE, "Quit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def show_normal(self):
        self.show()
        self.activateWindow()
        self.raise_()

    @Slot(str, dict)
    def _on_task_updated(self, task_id: str, data: dict):
        if (
            data.get("status") == "Completed"
            and self.tray_icon
            and config_manager.get("show_notifications", True)
        ):
            task = download_manager.tasks.get(task_id, {})
            title = task.get("title", "Download")
            self.tray_icon.showMessage(
                "Download Completed",
                f"'{title}' finished downloading.",
                QSystemTrayIcon.Information,
                3000,
            )

    # ── Appearance (called by Settings → Personalization) ────────────
    def set_theme_mode(self, mode: str):
        from qfluentwidgets import setTheme

        from .themes import THEME_MODES

        config_manager.set("theme_mode", mode)
        setTheme(THEME_MODES.get(mode, THEME_MODES["dark"]))

    def set_accent_color(self, hex_color: str):
        from qfluentwidgets import setThemeColor

        config_manager.set("accent_color", hex_color)
        setThemeColor(hex_color)
        InfoBar.success(
            "Accent color updated",
            "",
            duration=1500,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def switch_tab(self, index: int):
        pages = [self.downloader_tab, self.queue_tab, self.library_tab, self.settings_tab]
        if 0 <= index < len(pages):
            self.switchTo(pages[index])

    def _trigger_silent_update(self):
        logger.info("Triggering silent background update for yt-dlp...")
        self.silent_updater = YtdlUpdateWorker()
        self.silent_updater.update_finished.connect(self._on_silent_update_finished)
        self.silent_updater.start()

    @Slot(bool, str)
    def _on_silent_update_finished(self, success: bool, message: str):
        if success:
            logger.info("Silent update finished: yt-dlp is up to date.")
        else:
            logger.warning(f"Silent update check completed: {message}")

    def _check_and_download_ffmpeg(self):
        """Check if FFmpeg is available; silently download it if not."""
        custom_path = config_manager.get("ffmpeg_path", "")
        ff_path, _ = find_ffmpeg(custom_path or None)
        if ff_path:
            logger.info(f"FFmpeg found at startup: {ff_path}")
            return

        logger.info("FFmpeg not found at startup — triggering silent download.")
        InfoBar.info(
            "Setting up FFmpeg",
            "FFmpeg wasn't found — downloading it in the background now.",
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

        self.ffmpeg_silent_worker = FfmpegDownloadWorker()
        self.ffmpeg_silent_worker.download_finished.connect(self._on_ffmpeg_silent_finished)
        self.ffmpeg_silent_worker.start()

    @Slot(bool, str)
    def _on_ffmpeg_silent_finished(self, success: bool, message: str):
        if success:
            bin_dir = get_managed_ffmpeg_bin()
            if bin_dir:
                # Auto-save to config so subsequent launches skip the download
                config_manager.set("ffmpeg_path", str(bin_dir))
                # Refresh the settings tab display
                if hasattr(self, "settings_tab"):
                    self.settings_tab.ffmpeg_path_input.setText(str(bin_dir))
                    self.settings_tab._check_ffmpeg()
            logger.info("Silent FFmpeg download succeeded.")
            InfoBar.success(
                "FFmpeg ready",
                "FFmpeg was downloaded and is ready to use.",
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
        else:
            logger.warning(f"Silent FFmpeg download failed: {message}")
            InfoBar.warning(
                "FFmpeg auto-download failed",
                "Use Settings → Auto-Download FFmpeg to retry.",
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )

    @Slot(bool)
    def _on_network_status_changed(self, is_online: bool):
        download_manager.is_network_online = is_online
        download_manager.handle_network_status(is_online)

        if is_online:
            if self._offline_bar is not None:
                self._offline_bar.close()
                self._offline_bar = None
                InfoBar.success(
                    "Back online",
                    "Network connection restored — resuming paused downloads.",
                    duration=3000,
                    position=InfoBarPosition.TOP,
                    parent=self,
                )
        else:
            if self._offline_bar is None:
                self._offline_bar = InfoBar.warning(
                    "Offline",
                    "Network disconnected — active downloads have been paused.",
                    duration=-1,
                    position=InfoBarPosition.TOP,
                    parent=self,
                )
                self._offline_bar.closedSignal.connect(self._on_offline_bar_closed)

    def _on_offline_bar_closed(self):
        self._offline_bar = None

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.Type.WindowStateChange and (
            self.isMinimized() and config_manager.get("minimize_to_tray", True) and self.tray_icon
        ):
            self.hide()
            self.tray_icon.showMessage(
                APP_NAME,
                "App minimized to system tray.",
                QSystemTrayIcon.Information,
                1500,
            )
        super().changeEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "network_monitor"):
            self.network_monitor.stop()
            self.network_monitor.wait()
        config_manager.flush()
        download_manager.save_queue()
        event.accept()
