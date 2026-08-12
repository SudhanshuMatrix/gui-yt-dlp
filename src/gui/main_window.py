import os
import sys
from PySide6.QtCore import QEvent, Qt, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QStatusBar, QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget, QMenu
)
from .downloader_tab import DownloaderTab
from .library_tab import LibraryTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab, YtdlUpdateWorker
from .themes import get_stylesheet
from ..config import config_manager
from ..constants import APP_NAME, APP_VERSION, get_asset_path
from ..download_manager import download_manager
from ..utils.logger import get_logger
from ..utils.network_monitor import NetworkMonitor
from ..utils.ffmpeg_check import find_ffmpeg
from ..utils.ffmpeg_downloader import FfmpegDownloadWorker, get_managed_ffmpeg_bin

logger = get_logger("main_window")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - yt-dlp Desktop Frontend")
        self.resize(1000, 750)
        self.setMinimumSize(850, 600)

        # Set Window Icon
        logo_path = get_asset_path("logo.jpeg")
        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._init_ui()
        self._init_shortcuts()
        self._init_system_tray()

        # Apply user's preferred theme
        preferred_theme = config_manager.get("theme", "Midnight Obsidian")
        self.apply_theme(preferred_theme)

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
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header_frame = QFrame()
        header_frame.setObjectName("cardFrame")
        header_frame.setStyleSheet("""
            QFrame#cardFrame {
                border-radius: 0px; 
                border-top: none; 
                border-left: none; 
                border-right: none;
                background-color: rgb(26, 26, 30);
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title_icon_layout = QHBoxLayout()
        title_icon_layout.setSpacing(8)

        # Logo Icon
        logo_label = QLabel()
        logo_path = get_asset_path("logo.jpeg")
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setFixedSize(32, 32)
        else:
            logo_label.setVisible(False)
        title_icon_layout.addWidget(logo_label)

        # Brand Name / Title
        brand_label = QLabel("yt-dlp Flow")
        brand_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #ffffff; 
            background: transparent;
        """)
        title_icon_layout.addWidget(brand_label)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #71717a; font-size: 11px; margin-top: 6px;")
        title_icon_layout.addWidget(version_label)
        header_layout.addLayout(title_icon_layout)

        header_layout.addStretch()

        # Status information
        self.header_status = QLabel("Ready")
        self.header_status.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        header_layout.addWidget(self.header_status)

        main_layout.addWidget(header_frame)

        # 2. Main Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.downloader_tab = DownloaderTab(self)
        self.queue_tab = QueueTab()
        self.library_tab = LibraryTab(self)
        self.settings_tab = SettingsTab(self)

        self.tab_widget.addTab(self.downloader_tab, "Downloader")
        self.tab_widget.addTab(self.queue_tab, "Queue")
        self.tab_widget.addTab(self.library_tab, "Library")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        main_layout.addWidget(self.tab_widget)

        # 3. Status Bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"Welcome to {APP_NAME} v{APP_VERSION}")
        self.statusBar().setStyleSheet("color: #71717a; font-size: 11px; background-color: rgb(18, 18, 20); border-top: 1px solid rgb(44, 44, 53);")

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
        if not logo_path or not os.path.exists(logo_path) or not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(QIcon(logo_path), self)
        self.tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        tray_menu = QMenu()
        show_action = QAction("Show Application", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)

        pause_action = QAction("Pause All Downloads", self)
        pause_action.triggered.connect(lambda: download_manager.pause_all())
        tray_menu.addAction(pause_action)

        resume_action = QAction("Resume All Downloads", self)
        resume_action.triggered.connect(lambda: download_manager.resume_all())
        tray_menu.addAction(resume_action)

        tray_menu.addSeparator()
        quit_action = QAction("Quit", self)
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
        if data.get("status") == "Completed" and self.tray_icon and config_manager.get("show_notifications", True):
            task = download_manager.tasks.get(task_id, {})
            title = task.get("title", "Download")
            self.tray_icon.showMessage(
                "Download Completed",
                f"'{title}' finished downloading.",
                QSystemTrayIcon.Information,
                3000,
            )

    def apply_theme(self, theme_name: str):
        try:
            qss = get_stylesheet(theme_name)
            self.setStyleSheet(qss)
            self.statusBar().showMessage(f"Theme '{theme_name}' applied.")
            logger.info(f"Theme successfully applied: {theme_name}")
        except Exception as e:
            logger.error(f"Error applying theme {theme_name}: {e}")

    def switch_tab(self, index: int):
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)

    def _trigger_silent_update(self):
        logger.info("Triggering silent background update for yt-dlp...")
        self.silent_updater = YtdlUpdateWorker()
        self.silent_updater.update_finished.connect(self._on_silent_update_finished)
        self.silent_updater.start()

    @Slot(bool, str)
    def _on_silent_update_finished(self, success: bool, message: str):
        if success:
            logger.info("Silent update finished: yt-dlp is up to date.")
            self.statusBar().showMessage("yt-dlp is up to date.")
        else:
            logger.warning(f"Silent update check completed: {message}")
            self.statusBar().showMessage("yt-dlp update check completed.")

    def _check_and_download_ffmpeg(self):
        """Check if FFmpeg is available; silently download it if not."""
        custom_path = config_manager.get("ffmpeg_path", "")
        ff_path, _ = find_ffmpeg(custom_path or None)
        if ff_path:
            logger.info(f"FFmpeg found at startup: {ff_path}")
            return

        logger.info("FFmpeg not found at startup — triggering silent download.")
        self.statusBar().showMessage("FFmpeg not found. Downloading in background…")
        self.header_status.setText("Downloading FFmpeg…")
        self.header_status.setStyleSheet("color: #f59e0b; font-size: 12px;")

        self.ffmpeg_silent_worker = FfmpegDownloadWorker()
        self.ffmpeg_silent_worker.progress_updated.connect(self._on_ffmpeg_silent_progress)
        self.ffmpeg_silent_worker.download_finished.connect(self._on_ffmpeg_silent_finished)
        self.ffmpeg_silent_worker.start()

    @Slot(int, str)
    def _on_ffmpeg_silent_progress(self, percent: int, message: str):
        self.statusBar().showMessage(f"FFmpeg: {message} ({percent}%)")

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
            self.statusBar().showMessage("FFmpeg downloaded and ready!")
            self.header_status.setText("Ready")
            self.header_status.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        else:
            logger.warning(f"Silent FFmpeg download failed: {message}")
            self.statusBar().showMessage(
                "FFmpeg auto-download failed. Use Settings → Auto-Download FFmpeg to retry."
            )
            self.header_status.setText("Ready")
            self.header_status.setStyleSheet("color: #a1a1aa; font-size: 12px;")

    @Slot(bool)
    def _on_network_status_changed(self, is_online: bool):
        download_manager.is_network_online = is_online
        download_manager.handle_network_status(is_online)

        if is_online:
            self.header_status.setText("Ready")
            self.header_status.setStyleSheet("color: #a1a1aa; font-size: 12px;")
            self.statusBar().showMessage("Network connected.")
        else:
            self.header_status.setText("Offline (Downloads Paused)")
            self.header_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self.statusBar().showMessage("Network disconnected! Active downloads paused.")

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and config_manager.get("minimize_to_tray", True) and self.tray_icon:
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
