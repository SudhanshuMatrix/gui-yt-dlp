import os
import subprocess
import sys

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SettingCard,
    SettingCardGroup,
    SmoothScrollArea,
    SpinBox,
    SwitchButton,
    ToolButton,
)

from ..config import config_manager
from ..utils.ffmpeg_check import find_ffmpeg, get_ffmpeg_version
from ..utils.ffmpeg_downloader import FfmpegDownloadWorker, get_managed_ffmpeg_bin
from ..utils.logger import get_logger
from .themes import ACCENT_PRESETS, get_saved_theme_mode

THEME_MODE_LABELS: dict[str, str] = {"dark": "Dark", "light": "Light", "auto": "Follow System"}

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


class ColorSwatch(ToolButton):
    """A small round, click-to-select accent color swatch."""

    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setFixedSize(28, 28)
        self.setCheckable(True)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {self.hex_color};
                border-radius: 14px;
                border: 2px solid transparent;
            }}
            QToolButton:checked {{
                border: 2px solid white;
            }}
            """
        )


class SettingsTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.update_worker: YtdlUpdateWorker = None
        self.ffmpeg_dl_worker: FfmpegDownloadWorker = None
        self._init_ui()

    # ── Layout helpers ────────────────────────────────────────────────
    @staticmethod
    def _add_trailing(card: SettingCard, *widgets: QWidget):
        """Append control widget(s) to the right side of a SettingCard row,
        matching the layout pattern the library's own *SettingCard subclasses use."""
        for w in widgets:
            card.hBoxLayout.addWidget(w, 0)
            card.hBoxLayout.addSpacing(8)
        card.hBoxLayout.addSpacing(8)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # ── 0. Personalization ─────────────────────────────────────────
        appearance_group = SettingCardGroup("Personalization")

        theme_card = SettingCard(
            FluentIcon.BRIGHTNESS, "App Theme", "Dark, Light, or follow the OS setting"
        )
        self.theme_mode_combo = ComboBox()
        self.theme_mode_combo.addItems(list(THEME_MODE_LABELS.values()))
        current_mode = get_saved_theme_mode(config_manager)
        self.theme_mode_combo.setCurrentText(THEME_MODE_LABELS[current_mode])
        self.theme_mode_combo.currentTextChanged.connect(self._save_theme_mode)
        self.theme_mode_combo.setFixedWidth(160)
        self._add_trailing(theme_card, self.theme_mode_combo)
        appearance_group.addSettingCard(theme_card)

        accent_card = SettingCard(FluentIcon.PALETTE, "Accent Color", "Choose the app's accent color")
        swatch_row = QWidget()
        swatch_layout = QHBoxLayout(swatch_row)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setSpacing(6)
        current_accent = config_manager.get("accent_color", "#8b5cf6")
        self.accent_swatches: list[ColorSwatch] = []
        for hex_color in ACCENT_PRESETS.values():
            swatch = ColorSwatch(hex_color)
            swatch.setChecked(hex_color.lower() == current_accent.lower())
            swatch.clicked.connect(lambda _, c=hex_color: self._select_accent(c))
            swatch_layout.addWidget(swatch)
            self.accent_swatches.append(swatch)
        self._add_trailing(accent_card, swatch_row)
        appearance_group.addSettingCard(accent_card)

        layout.addWidget(appearance_group)

        # ── 1. Directories & Paths ─────────────────────────────────────
        path_group = SettingCardGroup("Directories & Paths")

        folder_card = SettingCard(FluentIcon.FOLDER, "Default Download Folder")
        self.download_path_input = LineEdit()
        self.download_path_input.setText(config_manager.get("download_directory"))
        self.download_path_input.setFixedWidth(260)
        self.download_path_input.textChanged.connect(self._save_download_path)
        self.folder_browse_btn = PushButton("Browse...")
        self.folder_browse_btn.clicked.connect(self._browse_download_folder)
        self._add_trailing(folder_card, self.download_path_input, self.folder_browse_btn)
        path_group.addSettingCard(folder_card)

        ffmpeg_card = SettingCard(
            FluentIcon.APPLICATION, "Custom FFmpeg Directory", "Optional — leave empty to auto-detect"
        )
        self.ffmpeg_path_input = LineEdit()
        self.ffmpeg_path_input.setText(config_manager.get("ffmpeg_path"))
        self.ffmpeg_path_input.setFixedWidth(260)
        self.ffmpeg_path_input.textChanged.connect(self._save_ffmpeg_path)
        self.ffmpeg_browse_btn = PushButton("Browse...")
        self.ffmpeg_browse_btn.clicked.connect(self._browse_ffmpeg_path)
        self._add_trailing(ffmpeg_card, self.ffmpeg_path_input, self.ffmpeg_browse_btn)
        path_group.addSettingCard(ffmpeg_card)

        self.ffmpeg_status_card = SettingCard(FluentIcon.INFO, "FFmpeg Status", "Checking...")
        path_group.addSettingCard(self.ffmpeg_status_card)

        install_card = SettingCard(
            FluentIcon.CLOUD_DOWNLOAD,
            "Automatic Install",
            "Download the latest GPL FFmpeg build from yt-dlp's GitHub releases",
        )
        self.ffmpeg_download_btn = PushButton(FluentIcon.DOWNLOAD, "Auto-Download FFmpeg")
        self.ffmpeg_download_btn.clicked.connect(self._download_ffmpeg)
        self._add_trailing(install_card, self.ffmpeg_download_btn)
        path_group.addSettingCard(install_card)

        self.ffmpeg_dl_progress = ProgressBar()
        self.ffmpeg_dl_progress.setRange(0, 100)
        self.ffmpeg_dl_progress.setValue(0)
        self.ffmpeg_dl_progress.setVisible(False)

        progress_card = SettingCard(FluentIcon.SYNC, "Download Progress")
        self._add_trailing(progress_card, self.ffmpeg_dl_progress)
        self.ffmpeg_progress_card = progress_card
        progress_card.setVisible(False)
        path_group.addSettingCard(progress_card)

        layout.addWidget(path_group)

        # ── 2. Download Preferences ─────────────────────────────────────
        pref_group = SettingCardGroup("Download Preferences")

        concurrency_card = SettingCard(
            FluentIcon.SPEED_HIGH, "Max Concurrent Downloads", "1-10 downloads running at once"
        )
        self.concurrency_spin = SpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(config_manager.get("concurrency", 3))
        self.concurrency_spin.valueChanged.connect(self._save_concurrency)
        self.concurrency_spin.setFixedWidth(100)
        self._add_trailing(concurrency_card, self.concurrency_spin)
        pref_group.addSettingCard(concurrency_card)

        container_card = SettingCard(FluentIcon.VIDEO, "Default Output Container")
        self.container_combo = ComboBox()
        self.container_combo.addItems(["Auto (Default)", "mp4", "mkv", "webm", "mov", "avi", "flv"])
        self.container_combo.setCurrentText(
            config_manager.get("default_video_container", "Auto (Default)")
        )
        self.container_combo.currentTextChanged.connect(self._save_default_video_container)
        self.container_combo.setFixedWidth(160)
        self._add_trailing(container_card, self.container_combo)
        pref_group.addSettingCard(container_card)

        layout.addWidget(pref_group)

        # ── 3. Speed & Network Optimization ─────────────────────────────
        speed_group = SettingCardGroup("Speed & Network Optimization")

        throttle_card = SettingCard(
            FluentIcon.SPEED_OFF,
            "Bypass Throttling",
            "Impersonate alternate player clients to avoid YouTube speed throttling",
        )
        self.bypass_throttling_switch = SwitchButton()
        self.bypass_throttling_switch.setChecked(config_manager.get("bypass_throttling", True))
        self.bypass_throttling_switch.checkedChanged.connect(self._save_bypass_throttling)
        self._add_trailing(throttle_card, self.bypass_throttling_switch)
        speed_group.addSettingCard(throttle_card)

        fragments_card = SettingCard(
            FluentIcon.SYNC, "Concurrent Fragment Downloads", "Parallel download threads per video"
        )
        self.fragments_spin = SpinBox()
        self.fragments_spin.setRange(1, 16)
        self.fragments_spin.setValue(config_manager.get("concurrent_fragments", 5))
        self.fragments_spin.valueChanged.connect(self._save_concurrent_fragments)
        self.fragments_spin.setFixedWidth(100)
        self._add_trailing(fragments_card, self.fragments_spin)
        speed_group.addSettingCard(fragments_card)

        chunk_card = SettingCard(FluentIcon.ZIP_FOLDER, "HTTP Chunk Size")
        self.chunk_combo = ComboBox()
        self.chunk_combo.addItems(["Disabled (Default)", "1 MB", "2 MB", "5 MB", "10 MB"])
        self.chunk_combo.setCurrentText(config_manager.get("http_chunk_size", "Disabled (Default)"))
        self.chunk_combo.currentTextChanged.connect(self._save_http_chunk_size)
        self.chunk_combo.setFixedWidth(160)
        self._add_trailing(chunk_card, self.chunk_combo)
        speed_group.addSettingCard(chunk_card)

        timeout_card = SettingCard(FluentIcon.WIFI, "Connection Timeout", "Socket timeout in seconds")
        self.timeout_spin = SpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(config_manager.get("socket_timeout", 20))
        self.timeout_spin.valueChanged.connect(self._save_socket_timeout)
        self.timeout_spin.setFixedWidth(100)
        self._add_trailing(timeout_card, self.timeout_spin)
        speed_group.addSettingCard(timeout_card)

        layout.addWidget(speed_group)

        # ── 4. System & Updates ──────────────────────────────────────────
        system_group = SettingCardGroup("System & Updates")

        notifications_card = SettingCard(
            FluentIcon.RINGER,
            "Desktop Notifications",
            "Show a system notification when a download completes",
        )
        self.notifications_switch = SwitchButton()
        self.notifications_switch.setChecked(config_manager.get("show_notifications", True))
        self.notifications_switch.checkedChanged.connect(self._save_show_notifications)
        self._add_trailing(notifications_card, self.notifications_switch)
        system_group.addSettingCard(notifications_card)

        minimize_card = SettingCard(
            FluentIcon.MINIMIZE,
            "Minimize to System Tray",
            "Keep running in the tray instead of closing when minimized",
        )
        self.minimize_tray_switch = SwitchButton()
        self.minimize_tray_switch.setChecked(config_manager.get("minimize_to_tray", True))
        self.minimize_tray_switch.checkedChanged.connect(self._save_minimize_to_tray)
        self._add_trailing(minimize_card, self.minimize_tray_switch)
        system_group.addSettingCard(minimize_card)

        auto_update_card = SettingCard(
            FluentIcon.UPDATE, "Auto-Check for Updates", "Check for yt-dlp updates on startup"
        )
        self.auto_update_switch = SwitchButton()
        self.auto_update_switch.setChecked(config_manager.get("auto_update", True))
        self.auto_update_switch.checkedChanged.connect(self._save_auto_update)
        self._add_trailing(auto_update_card, self.auto_update_switch)
        system_group.addSettingCard(auto_update_card)

        update_card = SettingCard(
            FluentIcon.SYNC, "yt-dlp Version", "Click update to fetch the latest yt-dlp binaries"
        )
        self.update_btn = PrimaryPushButton(FluentIcon.UPDATE, "Update Now")
        self.update_btn.clicked.connect(self._update_ytdl)
        self._add_trailing(update_card, self.update_btn)
        self.update_card = update_card
        system_group.addSettingCard(update_card)

        layout.addWidget(system_group)
        layout.addStretch()

        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)

        self._check_ffmpeg()

    def _toast(self, kind: str, title: str, content: str = ""):
        method = {"success": InfoBar.success, "warning": InfoBar.warning, "error": InfoBar.error}[
            kind
        ]
        method(title, content, duration=3500, position=InfoBarPosition.TOP, parent=self.window())

    def _check_ffmpeg(self):
        custom_ffmpeg = config_manager.get("ffmpeg_path")
        ff_path, _fp_path = find_ffmpeg(custom_ffmpeg)
        if ff_path:
            version = get_ffmpeg_version(ff_path)
            ver_str = f"detected version {version}" if version else "detected"
            self.ffmpeg_status_card.setContent(f"✓ Available ({ver_str}) at {ff_path}")
        else:
            self.ffmpeg_status_card.setContent(
                "✗ Not found! Audio conversion & merging will fail."
            )

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
    def _save_default_video_container(self, val: str):
        config_manager.set("default_video_container", val)

    @Slot(str)
    def _save_theme_mode(self, label: str):
        mode = next((k for k, v in THEME_MODE_LABELS.items() if v == label), "dark")
        self.main_window.set_theme_mode(mode)

    def _select_accent(self, hex_color: str):
        for swatch in self.accent_swatches:
            swatch.setChecked(swatch.hex_color.lower() == hex_color.lower())
        self.main_window.set_accent_color(hex_color)

    @Slot(bool)
    def _save_show_notifications(self, is_checked: bool):
        config_manager.set("show_notifications", is_checked)

    @Slot(bool)
    def _save_minimize_to_tray(self, is_checked: bool):
        config_manager.set("minimize_to_tray", is_checked)

    @Slot(bool)
    def _save_auto_update(self, is_checked: bool):
        config_manager.set("auto_update", is_checked)

    @Slot(bool)
    def _save_bypass_throttling(self, is_checked: bool):
        config_manager.set("bypass_throttling", is_checked)

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
        self.ffmpeg_progress_card.setVisible(True)
        self.ffmpeg_dl_progress.setVisible(True)
        self.ffmpeg_dl_progress.setValue(0)
        self.ffmpeg_progress_card.setContent("Starting download…")

        self.ffmpeg_dl_worker = FfmpegDownloadWorker()
        self.ffmpeg_dl_worker.progress_updated.connect(self._on_ffmpeg_dl_progress)
        self.ffmpeg_dl_worker.download_finished.connect(self._on_ffmpeg_dl_finished)
        self.ffmpeg_dl_worker.start()

    @Slot(int, str)
    def _on_ffmpeg_dl_progress(self, percent: int, message: str):
        self.ffmpeg_dl_progress.setValue(percent)
        self.ffmpeg_progress_card.setContent(message)

    @Slot(bool, str)
    def _on_ffmpeg_dl_finished(self, success: bool, message: str):
        self.ffmpeg_download_btn.setEnabled(True)
        self.ffmpeg_progress_card.setVisible(False)
        if success:
            # Auto-save the detected bin path into config
            bin_dir = get_managed_ffmpeg_bin()
            if bin_dir:
                self.ffmpeg_path_input.setText(str(bin_dir))
            self._check_ffmpeg()
            self._toast("success", "FFmpeg Ready", message)
        else:
            self._toast("error", "FFmpeg Download Failed", message)

    @Slot()
    def _update_ytdl(self):
        if getattr(sys, "frozen", False):
            self._toast(
                "warning",
                "System Managed",
                "This is a packaged standalone binary — the bundled yt-dlp "
                "version is managed by the package builder.",
            )
            return

        self.update_btn.setEnabled(False)
        self.update_btn.setText("Updating...")
        self.update_card.setContent("Downloading and installing latest yt-dlp binaries...")

        self.update_worker = YtdlUpdateWorker()
        self.update_worker.update_finished.connect(self._on_update_completed)
        self.update_worker.start()

    @Slot(bool, str)
    def _on_update_completed(self, success: bool, message: str):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Update Now")
        self.update_card.setContent(message)

        if success:
            self._toast("success", "Update Success", message)
        else:
            self._toast("error", "Update Failed", message)
