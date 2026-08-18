import os
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import config_manager
from ..gui.themes import THEMES
from ..utils.ffmpeg_check import find_ffmpeg, get_ffmpeg_version
from ..utils.ffmpeg_downloader import FfmpegDownloadWorker, get_managed_ffmpeg_bin
from ..utils.logger import get_logger

logger = get_logger("settings_tab")


class YtdlUpdateWorker(QThread):
    update_finished = Signal(bool, str)

    def run(self):
        try:
            logger.info("Starting yt-dlp update process via sys.executable...")

            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            logger.debug(f"Running update command: {' '.join(cmd)}")

            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
            )

            if result.returncode == 0:
                ver_check = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import yt_dlp; print(getattr(yt_dlp, '__version__', 'unknown'))",
                    ],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo,
                )
                version_str = ver_check.stdout.strip() or "latest"
                logger.info(f"yt-dlp updated successfully to {version_str}.")
                self.update_finished.emit(True, f"yt-dlp updated successfully to {version_str}.")
            else:
                logger.error(f"yt-dlp update failed: {result.stderr}")
                self.update_finished.emit(False, f"Update failed: {result.stderr or result.stdout}")
        except Exception as e:
            logger.error(f"Error during yt-dlp update: {e}")
            self.update_finished.emit(False, f"Error: {e!s}")


class SettingsTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.update_worker: YtdlUpdateWorker = None
        self.ffmpeg_dl_worker: FfmpegDownloadWorker = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content.setStyleSheet("QWidget#scrollContent { background-color: transparent; }")

        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. Download Path Group
        path_group = QGroupBox("Directories & Paths")
        path_layout = QFormLayout(path_group)
        path_layout.setContentsMargins(16, 20, 16, 16)
        path_layout.setSpacing(12)
        path_layout.setLabelAlignment(Qt.AlignLeft)
        path_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Download Folder
        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        self.download_path_input = QLineEdit(config_manager.get("download_directory"))
        self.download_path_input.textChanged.connect(self._save_download_path)
        folder_layout.addWidget(self.download_path_input)
        self.folder_browse_btn = QPushButton("Browse...")
        self.folder_browse_btn.clicked.connect(self._browse_download_folder)
        folder_layout.addWidget(self.folder_browse_btn)
        path_layout.addRow("Default Download Folder:", folder_widget)

        # FFmpeg Path
        ffmpeg_widget = QWidget()
        ffmpeg_layout = QHBoxLayout(ffmpeg_widget)
        ffmpeg_layout.setContentsMargins(0, 0, 0, 0)
        ffmpeg_layout.setSpacing(8)
        self.ffmpeg_path_input = QLineEdit(config_manager.get("ffmpeg_path"))
        self.ffmpeg_path_input.textChanged.connect(self._save_ffmpeg_path)
        ffmpeg_layout.addWidget(self.ffmpeg_path_input)
        self.ffmpeg_browse_btn = QPushButton("Browse...")
        self.ffmpeg_browse_btn.clicked.connect(self._browse_ffmpeg_path)
        ffmpeg_layout.addWidget(self.ffmpeg_browse_btn)
        path_layout.addRow("Custom FFmpeg Directory (Optional):", ffmpeg_widget)

        # FFmpeg version label
        self.ffmpeg_ver_label = QLabel("FFmpeg Status: Checking...")
        self.ffmpeg_ver_label.setStyleSheet("color: #71717a; font-size: 11px;")
        path_layout.addRow(self.ffmpeg_ver_label)

        # Auto-download row
        dl_widget = QWidget()
        dl_layout = QHBoxLayout(dl_widget)
        dl_layout.setContentsMargins(0, 0, 0, 0)
        dl_layout.setSpacing(8)

        self.ffmpeg_download_btn = QPushButton("⬇  Auto-Download FFmpeg")
        self.ffmpeg_download_btn.setToolTip(
            "Automatically download the latest GPL FFmpeg build "
            "from yt-dlp's official GitHub releases into the app's config folder."
        )
        self.ffmpeg_download_btn.clicked.connect(self._download_ffmpeg)
        dl_layout.addWidget(self.ffmpeg_download_btn)

        self.ffmpeg_dl_progress = QProgressBar()
        self.ffmpeg_dl_progress.setRange(0, 100)
        self.ffmpeg_dl_progress.setValue(0)
        self.ffmpeg_dl_progress.setVisible(False)
        self.ffmpeg_dl_progress.setFixedHeight(18)
        self.ffmpeg_dl_progress.setTextVisible(True)
        dl_layout.addWidget(self.ffmpeg_dl_progress)

        self.ffmpeg_dl_status = QLabel("")
        self.ffmpeg_dl_status.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        dl_layout.addWidget(self.ffmpeg_dl_status)
        dl_layout.setStretch(2, 1)

        path_layout.addRow("Automatic Install:", dl_widget)
        layout.addWidget(path_group)

        # 2. Preferences Group
        pref_group = QGroupBox("Download Preferences")
        pref_layout = QFormLayout(pref_group)
        pref_layout.setContentsMargins(16, 20, 16, 16)
        pref_layout.setSpacing(12)
        pref_layout.setLabelAlignment(Qt.AlignLeft)
        pref_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(config_manager.get("concurrency", 3))
        self.concurrency_spin.valueChanged.connect(self._save_concurrency)
        self.concurrency_spin.setFixedWidth(100)
        pref_layout.addRow("Max Concurrent Downloads:", self.concurrency_spin)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(config_manager.get("theme", "Midnight Obsidian"))
        self.theme_combo.currentTextChanged.connect(self._save_theme)
        self.theme_combo.setFixedWidth(180)
        pref_layout.addRow("App Theme Selection:", self.theme_combo)

        layout.addWidget(pref_group)

        # 3. Speed & Network Optimization Group
        speed_group = QGroupBox("Speed & Network Optimization")
        speed_layout = QFormLayout(speed_group)
        speed_layout.setContentsMargins(16, 20, 16, 16)
        speed_layout.setSpacing(12)
        speed_layout.setLabelAlignment(Qt.AlignLeft)
        speed_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.bypass_throttling_check = QCheckBox(
            "Bypass YouTube download speed throttling (impersonate player clients)"
        )
        self.bypass_throttling_check.setChecked(config_manager.get("bypass_throttling", True))
        self.bypass_throttling_check.stateChanged.connect(self._save_bypass_throttling)
        speed_layout.addRow(self.bypass_throttling_check)

        self.fragments_spin = QSpinBox()
        self.fragments_spin.setRange(1, 16)
        self.fragments_spin.setValue(config_manager.get("concurrent_fragments", 5))
        self.fragments_spin.valueChanged.connect(self._save_concurrent_fragments)
        self.fragments_spin.setFixedWidth(100)
        speed_layout.addRow("Concurrent Fragment Downloads:", self.fragments_spin)

        self.chunk_combo = QComboBox()
        self.chunk_combo.addItems(["Disabled (Default)", "1 MB", "2 MB", "5 MB", "10 MB"])
        self.chunk_combo.setCurrentText(config_manager.get("http_chunk_size", "Disabled (Default)"))
        self.chunk_combo.currentTextChanged.connect(self._save_http_chunk_size)
        self.chunk_combo.setFixedWidth(180)
        speed_layout.addRow("HTTP Chunk Size:", self.chunk_combo)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(config_manager.get("socket_timeout", 20))
        self.timeout_spin.valueChanged.connect(self._save_socket_timeout)
        self.timeout_spin.setFixedWidth(100)
        speed_layout.addRow("Connection Timeout (seconds):", self.timeout_spin)

        layout.addWidget(speed_group)

        # 4. System Options & Updates Group
        system_group = QGroupBox("System & Updates")
        system_layout = QVBoxLayout(system_group)
        system_layout.setContentsMargins(16, 20, 16, 16)
        system_layout.setSpacing(12)

        self.auto_update_check = QCheckBox("Auto-check for yt-dlp updates on startup")
        self.auto_update_check.setChecked(config_manager.get("auto_update", True))
        self.auto_update_check.stateChanged.connect(self._save_auto_update)
        system_layout.addWidget(self.auto_update_check)

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

        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)

        self._check_ffmpeg()

    def _check_ffmpeg(self):
        custom_ffmpeg = config_manager.get("ffmpeg_path")
        ff_path, _fp_path = find_ffmpeg(custom_ffmpeg)
        if ff_path:
            version = get_ffmpeg_version(ff_path)
            ver_str = f"detected version {version}" if version else "detected"
            self.ffmpeg_ver_label.setText(f"FFmpeg Status: Available ({ver_str}) at {ff_path}")
            self.ffmpeg_ver_label.setStyleSheet("color: #10b981; font-size: 11px;")
        else:
            self.ffmpeg_ver_label.setText(
                "FFmpeg Status: Not Found! Audio conversion & merging will fail."
            )
            self.ffmpeg_ver_label.setStyleSheet("color: #ef4444; font-size: 11px;")

    @Slot()
    def _browse_download_folder(self):
        current_dir = self.download_path_input.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(
            self, "Select Default Download Folder", current_dir
        )
        if folder:
            self.download_path_input.setText(folder)

    @Slot()
    def _browse_ffmpeg_path(self):
        current = self.ffmpeg_path_input.text() or ""
        # Ask user if they want to select an executable or a directory
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select FFmpeg Executable (ffmpeg / ffmpeg.exe)",
            current,
            "Executable Files (ffmpeg* *.exe);;All Files (*)",
        )
        if file_path:
            self.ffmpeg_path_input.setText(file_path)
        else:
            folder = QFileDialog.getExistingDirectory(
                self, "Or Select FFmpeg Binaries Directory", current
            )
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
        self.main_window.apply_theme(theme_name)

    @Slot(int)
    def _save_auto_update(self, state: int):
        config_manager.set("auto_update", state == Qt.Checked.value)

    @Slot(int)
    def _save_bypass_throttling(self, state: int):
        config_manager.set("bypass_throttling", state == Qt.Checked.value)

    @Slot(int)
    def _save_concurrent_fragments(self, val: int):
        config_manager.set("concurrent_fragments", val)

    @Slot(str)
    def _save_http_chunk_size(self, text: str):
        config_manager.set("http_chunk_size", text)

    @Slot(int)
    def _save_socket_timeout(self, val: int):
        config_manager.set("socket_timeout", val)

    @Slot()
    def _download_ffmpeg(self):
        """Start background FFmpeg auto-download."""
        self.ffmpeg_download_btn.setEnabled(False)
        self.ffmpeg_dl_progress.setVisible(True)
        self.ffmpeg_dl_progress.setValue(0)
        self.ffmpeg_dl_status.setText("Starting download…")
        self.ffmpeg_dl_status.setStyleSheet("color: #a1a1aa; font-size: 11px;")

        self.ffmpeg_dl_worker = FfmpegDownloadWorker()
        self.ffmpeg_dl_worker.progress_updated.connect(self._on_ffmpeg_dl_progress)
        self.ffmpeg_dl_worker.download_finished.connect(self._on_ffmpeg_dl_finished)
        self.ffmpeg_dl_worker.start()

    @Slot(int, str)
    def _on_ffmpeg_dl_progress(self, percent: int, message: str):
        self.ffmpeg_dl_progress.setValue(percent)
        self.ffmpeg_dl_status.setText(message)

    @Slot(bool, str)
    def _on_ffmpeg_dl_finished(self, success: bool, message: str):
        self.ffmpeg_download_btn.setEnabled(True)
        self.ffmpeg_dl_progress.setVisible(False)
        if success:
            self.ffmpeg_dl_status.setText("✓ FFmpeg installed!")
            self.ffmpeg_dl_status.setStyleSheet("color: #10b981; font-size: 11px;")
            # Auto-save the detected bin path into config
            bin_dir = get_managed_ffmpeg_bin()
            if bin_dir:
                self.ffmpeg_path_input.setText(str(bin_dir))
            self._check_ffmpeg()
            QMessageBox.information(self, "FFmpeg Ready", message)
        else:
            self.ffmpeg_dl_status.setText("✗ Download failed")
            self.ffmpeg_dl_status.setStyleSheet("color: #ef4444; font-size: 11px;")
            QMessageBox.critical(self, "FFmpeg Download Failed", message)

    @Slot()
    def _update_ytdl(self):
        if getattr(sys, "frozen", False):
            QMessageBox.information(
                self,
                "System Managed",
                "This application is running as a packaged standalone binary. "
                "The bundled yt-dlp version is managed by the package builder.",
            )
            return

        self.update_btn.setEnabled(False)
        self.update_btn.setText("Updating...")
        self.update_status_label.setText("Downloading and installing latest yt-dlp binaries...")
        self.update_status_label.setStyleSheet("color: #a7f3d0; font-size: 12px;")

        self.update_worker = YtdlUpdateWorker()
        self.update_worker.update_finished.connect(self._on_update_completed)
        self.update_worker.start()

    @Slot(bool, str)
    def _on_update_completed(self, success: bool, message: str):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Update yt-dlp Now")
        self.update_status_label.setText(message)

        if success:
            self.update_status_label.setStyleSheet("color: #10b981; font-size: 12px;")
            QMessageBox.information(self, "Update Success", message)
        else:
            self.update_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            QMessageBox.critical(self, "Update Failed", message)
