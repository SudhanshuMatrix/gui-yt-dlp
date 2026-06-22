import os
import sys
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QStatusBar
)
from PySide6.QtGui import QPixmap, QIcon
from .downloader_tab import DownloaderTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab, YtdlUpdateWorker
from .themes import get_stylesheet
from ..config import config_manager
from ..utils.logger import get_logger

logger = get_logger("main_window")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp Desktop Frontend")
        self.resize(1000, 750)
        self.setMinimumSize(850, 600)
        
        # Set Window Icon
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        
        self._init_ui()
        
        # Apply the user's preferred theme
        preferred_theme = config_manager.get("theme", "Midnight Obsidian")
        self.apply_theme(preferred_theme)
        
        # Trigger background auto-update if enabled (skipped for system-installed deb packages)
        if config_manager.get("auto_update", True) and not getattr(sys, 'frozen', False):
            self._trigger_silent_update()

    def _init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Premium Header Bar
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
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
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
        
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #71717a; font-size: 11px; margin-top: 6px;")
        title_icon_layout.addWidget(version_label)
        header_layout.addLayout(title_icon_layout)
        
        header_layout.addStretch()
        
        # Status information
        self.header_status = QLabel("Ready")
        self.header_status.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        header_layout.addWidget(self.header_status)
        
        main_layout.addWidget(header_frame)

        # 2. Main content area containing QTabWidget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Instantiate tabs
        self.downloader_tab = DownloaderTab(self)
        self.queue_tab = QueueTab()
        self.settings_tab = SettingsTab(self)
        
        self.tab_widget.addTab(self.downloader_tab, "Downloader")
        self.tab_widget.addTab(self.queue_tab, "Queue")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        main_layout.addWidget(self.tab_widget)
        
        # 3. Status Bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Welcome to yt-dlp Desktop Frontend")
        self.statusBar().setStyleSheet("color: #71717a; font-size: 11px; background-color: rgb(18, 18, 20); border-top: 1px solid rgb(44, 44, 53);")

    def apply_theme(self, theme_name: str):
        """Load and apply QSS stylesheet for the chosen theme."""
        try:
            qss = get_stylesheet(theme_name)
            self.setStyleSheet(qss)
            self.statusBar().showMessage(f"Theme '{theme_name}' applied.")
            logger.info(f"Theme successfully applied: {theme_name}")
        except Exception as e:
            logger.error(f"Error applying theme {theme_name}: {e}")

    def switch_tab(self, index: int):
        """Switch to a specific tab by index."""
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)

    def _trigger_silent_update(self):
        """Run yt-dlp update check silently in the background on startup."""
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
