import os
import sys
import subprocess
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSpinBox, QComboBox, QCheckBox, QGroupBox, 
    QFileDialog, QMessageBox
)
from ..config import config_manager
from ..gui.themes import THEMES
from ..utils.logger import get_logger
from ..utils.ffmpeg_check import find_ffmpeg, get_ffmpeg_version

logger = get_logger("settings_tab")

class YtdlUpdateWorker(QThread):
    update_finished = Signal(bool, str)

    def run(self):
        try:
            logger.info("Starting yt-dlp update process...")
            
            # Determine path to pip in virtual env or system
            # sys.prefix points to virtual env root if running inside venv
            venv_bin = os.path.dirname(sys.executable)
            pip_path = os.path.join(venv_bin, "pip")
            
            if not os.path.exists(pip_path):
                # Fallback to default pip path
                pip_path = os.path.join(venv_bin, "pip3")
                
            if not os.path.exists(pip_path):
                pip_path = "pip" # System PATH fallback

            cmd = [pip_path, "install", "--upgrade", "yt-dlp"]
            logger.debug(f"Running update command: {' '.join(cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            if result.returncode == 0:
                # Retrieve new version
                ver_check = subprocess.run(
                    [sys.executable, "-c", "import yt_dlp; print(yt_dlp.__name__)"],
                    stdout=subprocess.PIPE,
                    text=True,
                    startupinfo=startupinfo
                )
                logger.info("yt-dlp updated successfully.")
                self.update_finished.emit(True, "yt-dlp has been updated to the latest version.")
            else:
                logger.error(f"yt-dlp update failed: {result.stderr}")
                self.update_finished.emit(False, f"Update failed: {result.stderr or result.stdout}")
        except Exception as e:
            logger.error(f"Error during yt-dlp update: {e}")
            self.update_finished.emit(False, f"Error: {str(e)}")


class SettingsTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.update_worker: YtdlUpdateWorker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. Download Path Group
        path_group = QGroupBox("Directories & Paths")
        path_layout = QVBoxLayout(path_group)
        path_layout.setSpacing(12)
        
        # Download Folder
        folder_label_layout = QHBoxLayout()
        folder_label_layout.addWidget(QLabel("Default Download Folder:"))
        path_layout.addLayout(folder_label_layout)
        
        folder_layout = QHBoxLayout()
        self.download_path_input = QLineEdit(config_manager.get("download_directory"))
        self.download_path_input.textChanged.connect(self._save_download_path)
        folder_layout.addWidget(self.download_path_input)
        
        self.folder_browse_btn = QPushButton("Browse...")
        self.folder_browse_btn.clicked.connect(self._browse_download_folder)
        folder_layout.addWidget(self.folder_browse_btn)
        path_layout.addLayout(folder_layout)

        # FFmpeg Path
        ffmpeg_label_layout = QHBoxLayout()
        ffmpeg_label_layout.addWidget(QLabel("Custom FFmpeg Directory (Optional):"))
        path_layout.addLayout(ffmpeg_label_layout)
        
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_path_input = QLineEdit(config_manager.get("ffmpeg_path"))
        self.ffmpeg_path_input.textChanged.connect(self._save_ffmpeg_path)
        ffmpeg_layout.addWidget(self.ffmpeg_path_input)
        
        self.ffmpeg_browse_btn = QPushButton("Browse...")
        self.ffmpeg_browse_btn.clicked.connect(self._browse_ffmpeg_folder)
        ffmpeg_layout.addWidget(self.ffmpeg_browse_btn)
        path_layout.addLayout(ffmpeg_layout)

        # FFmpeg version label
        self.ffmpeg_ver_label = QLabel("FFmpeg Status: Checking...")
        self.ffmpeg_ver_label.setStyleSheet("color: #71717a; font-size: 11px;")
        path_layout.addWidget(self.ffmpeg_ver_label)
        
        layout.addWidget(path_group)

        # 2. Preferences Group
        pref_group = QGroupBox("Download Preferences")
        pref_layout = QVBoxLayout(pref_group)
        pref_layout.setSpacing(12)
        
        # Concurrency limit
        concurrency_layout = QHBoxLayout()
        concurrency_layout.addWidget(QLabel("Max Concurrent Downloads:"))
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(config_manager.get("concurrency", 3))
        self.concurrency_spin.valueChanged.connect(self._save_concurrency)
        concurrency_layout.addWidget(self.concurrency_spin)
        concurrency_layout.addStretch()
        pref_layout.addLayout(concurrency_layout)
        
        # Theme dropdown
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("App Theme Selection:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(config_manager.get("theme", "Midnight Obsidian"))
        self.theme_combo.currentTextChanged.connect(self._save_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        pref_layout.addLayout(theme_layout)

        layout.addWidget(pref_group)

        # 3. System Options & Updates Group
        system_group = QGroupBox("System & Updates")
        system_layout = QVBoxLayout(system_group)
        system_layout.setSpacing(12)
        
        # Auto Update
        self.auto_update_check = QCheckBox("Auto-check for yt-dlp updates on startup")
        self.auto_update_check.setChecked(config_manager.get("auto_update", True))
        self.auto_update_check.stateChanged.connect(self._save_auto_update)
        system_layout.addWidget(self.auto_update_check)
        
        # Update Button Row
        update_btn_layout = QHBoxLayout()
        self.update_btn = QPushButton("Update yt-dlp Now")
        self.update_btn.clicked.connect(self._update_ytdl)
        update_btn_layout.addWidget(self.update_btn)
        
        self.update_status_label = QLabel("Click update to fetch latest yt-dlp binaries.")
        self.update_status_label.setStyleSheet("color: #71717a; font-size: 12px;")
        update_btn_layout.addWidget(self.update_status_label)
        update_btn_layout.setStretch(1, 1)
        system_layout.addLayout(update_btn_layout)
        
        layout.addWidget(system_group)
        layout.addStretch()

        # Initial checks
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        custom_ffmpeg = config_manager.get("ffmpeg_path")
        ff_path, fp_path = find_ffmpeg(custom_ffmpeg)
        if ff_path:
            version = get_ffmpeg_version(ff_path)
            ver_str = f"detected version {version}" if version else "detected"
            self.ffmpeg_ver_label.setText(f"FFmpeg Status: Available ({ver_str}) at {ff_path}")
            self.ffmpeg_ver_label.setStyleSheet("color: #10b981; font-size: 11px;") # green
        else:
            self.ffmpeg_ver_label.setText("FFmpeg Status: Not Found! Audio conversion & merging will fail.")
            self.ffmpeg_ver_label.setStyleSheet("color: #ef4444; font-size: 11px;") # red

    @Slot()
    def _browse_download_folder(self):
        current_dir = self.download_path_input.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Folder", current_dir)
        if folder:
            self.download_path_input.setText(folder)

    @Slot()
    def _browse_ffmpeg_folder(self):
        current_dir = self.ffmpeg_path_input.text() or "/"
        # Can select either the executable itself or its containing directory
        folder = QFileDialog.getExistingDirectory(self, "Select FFmpeg Binaries Directory", current_dir)
        if folder:
            self.ffmpeg_path_input.setText(folder)

    @Slot(str)
    def _save_download_path(self, text: str):
        config_manager.set("download_directory", text.strip())

    @Slot(str)
    def _save_ffmpeg_path(self, text: str):
        config_manager.set("ffmpeg_path", text.strip())
        self._check_ffmpeg()

    @Slot(int)
    def _save_concurrency(self, val: int):
        config_manager.set("concurrency", val)

    @Slot(str)
    def _save_theme(self, theme_name: str):
        config_manager.set("theme", theme_name)
        # Apply theme immediately across the main application
        self.main_window.apply_theme(theme_name)

    @Slot(int)
    def _save_auto_update(self, state: int):
        config_manager.set("auto_update", state == Qt.Checked.value)

    @Slot()
    def _update_ytdl(self):
        if getattr(sys, 'frozen', False):
            QMessageBox.information(
                self, 
                "System Managed", 
                "This application is running as a packaged standalone binary. "
                "The bundled yt-dlp version is managed by the package builder. "
                "To get the latest version of yt-dlp, please update the gui-yt-dlp application."
            )
            return

        self.update_btn.setEnabled(False)
        self.update_btn.setText("Updating...")
        self.update_status_label.setText("Downloading and installing latest yt-dlp binaries...")
        self.update_status_label.setStyleSheet("color: #a7f3d0; font-size: 12px;") # light emerald
        
        self.update_worker = YtdlUpdateWorker()
        self.update_worker.update_finished.connect(self._on_update_completed)
        self.update_worker.start()

    @Slot(bool, str)
    def _on_update_completed(self, success: bool, message: str):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Update yt-dlp Now")
        self.update_status_label.setText(message)
        
        if success:
            self.update_status_label.setStyleSheet("color: #10b981; font-size: 12px;") # green
            QMessageBox.information(self, "Update Success", message)
        else:
            self.update_status_label.setStyleSheet("color: #ef4444; font-size: 12px;") # red
            QMessageBox.critical(self, "Update Failed", message)
