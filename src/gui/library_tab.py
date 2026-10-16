import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    StrongBodyLabel,
    TableWidget,
    ToolButton,
    TransparentToolButton,
)

from ..utils.library_manager import library_manager
from ..utils.logger import get_logger
from ..utils.url_sanitizer import is_valid_url, sanitize_url
from ..yt_dlp_worker import VideoAnalyzer

logger = get_logger("library_tab")


class LibraryTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.analyzer = None
        self.terminating_analyzers = set()
        self._filter_text = ""

        self._init_ui()
        self.refresh_library()

    def _toast(self, kind: str, title: str, content: str = ""):
        method = {"success": InfoBar.success, "warning": InfoBar.warning, "error": InfoBar.error}[
            kind
        ]
        method(title, content, duration=3500, position=InfoBarPosition.TOP, parent=self.window())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 1. Quick Add Section
        add_layout = QHBoxLayout()
        add_layout.setSpacing(10)

        add_layout.addWidget(CaptionLabel("Quick Save URL:"))
        self.url_input = LineEdit()
        self.url_input.setPlaceholderText("Paste video or playlist URL to save for later...")
        self.url_input.setClearButtonEnabled(True)
        add_layout.addWidget(self.url_input, 1)

        self.add_btn = PrimaryPushButton(FluentIcon.SAVE, "Save")
        self.add_btn.clicked.connect(self._quick_add)
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        # 2. Header Status
        header_row = QHBoxLayout()
        self.count_label = StrongBodyLabel("Saved Items: 0")
        header_row.addWidget(self.count_label)
        header_row.addStretch()

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Filter by title or channel...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self._on_filter_changed)
        self.search_input.searchSignal.connect(self._on_filter_changed)
        self.search_input.clearSignal.connect(lambda: self._on_filter_changed(""))
        header_row.addWidget(self.search_input)

        self.refresh_btn = PushButton(FluentIcon.SYNC, "Refresh")
        self.refresh_btn.clicked.connect(self.refresh_library)
        header_row.addWidget(self.refresh_btn)

        layout.addLayout(header_row)

        # 3. Library Table
        self.table = TableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Thumbnail", "Title & Channel", "Details", "Date Added", "Actions"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)

        # Header configuration
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Thumbnail
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title & Channel
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Details
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Date Added
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Actions

        self.table.setColumnWidth(0, 90)  # Thumbnail
        self.table.setColumnWidth(4, 160)  # Actions (Load, Download, Remove)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def _on_filter_changed(self, text: str):
        self._filter_text = text.strip().lower()
        self.refresh_library()

    def refresh_library(self):
        self.table.setRowCount(0)
        items = library_manager.items

        if self._filter_text:
            items = [
                item
                for item in items
                if self._filter_text in item.get("title", "").lower()
                or self._filter_text in item.get("uploader", "").lower()
            ]
            self.count_label.setText(
                f"Saved Items: {len(items)} / {len(library_manager.items)}"
            )
        else:
            self.count_label.setText(f"Saved Items: {len(library_manager.items)}")

        for row, item in enumerate(items):
            self.table.insertRow(row)

            # Column 0: Thumbnail
            thumb_label = CaptionLabel()
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setFixedSize(80, 45)
            self._set_thumbnail_on_label(thumb_label, item.get("thumbnail_local_path"))
            self.table.setCellWidget(row, 0, thumb_label)

            # Column 1: Title & Channel
            title = item.get("title", "Unknown Title")
            uploader = item.get("uploader", "Unknown Channel")
            title_text = f"<b>{title}</b><br/><span style='font-size: 11px;'>{uploader}</span>"

            title_label = CaptionLabel()
            title_label.setText(title_text)
            title_label.setTextFormat(Qt.RichText)
            title_label.setWordWrap(True)
            title_label.setStyleSheet("padding: 4px;")
            self.table.setCellWidget(row, 1, title_label)

            # Column 2: Details
            type_str = item.get("type", "Video")
            duration = item.get("duration", "Unknown")
            details_text = f"{type_str}\n({duration})"
            details_item = QTableWidgetItem(details_text)
            details_item.setFlags(details_item.flags() & ~Qt.ItemIsEditable)
            details_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 2, details_item)

            # Column 3: Date Added
            date_item = QTableWidgetItem(item.get("added_at", "Unknown"))
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
            date_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 3, date_item)

            # Column 4: Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)

            load_btn = ToolButton(FluentIcon.EDIT)
            load_btn.setToolTip("Configure & analyze")
            load_btn.clicked.connect(lambda _, url=item["url"]: self._load_item(url))

            dl_btn = ToolButton(FluentIcon.CLOUD_DOWNLOAD)
            dl_btn.setToolTip("Quick download")
            dl_btn.clicked.connect(lambda _, it=item: self._quick_download_item(it))

            remove_btn = TransparentToolButton(FluentIcon.DELETE)
            remove_btn.setToolTip("Remove")
            remove_btn.clicked.connect(lambda _, url=item["url"]: self._remove_item(url))

            actions_layout.addWidget(load_btn)
            actions_layout.addWidget(dl_btn)
            actions_layout.addWidget(remove_btn)
            actions_layout.addStretch()
            self.table.setCellWidget(row, 4, actions_widget)

    def _set_thumbnail_on_label(self, label: CaptionLabel, path: str):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            label.setPixmap(
                pixmap.scaled(
                    label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            label.setText("No Preview")

    def _load_item(self, url: str):
        """Switch to Downloader tab and analyze the URL."""
        self.main_window.downloader_tab.url_input.setText(url)
        self.main_window.switch_tab(0)  # Downloader is 0
        self.main_window.downloader_tab._start_analysis()

    def _quick_download_item(self, item: dict):
        """Immediately add the item to the download queue using default options."""
        url = item["url"]
        title = item["title"]
        type_str = item.get("type", "Video")

        from ..config import config_manager
        from ..download_manager import download_manager

        ydl_opts = {
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "format": "bestvideo+bestaudio/best",
        }

        # Add Speed & Performance optimizations from settings
        concurrent_frags = config_manager.get("concurrent_fragments", 5)
        ydl_opts["concurrent_fragment_downloads"] = concurrent_frags

        chunk_size = config_manager.get("http_chunk_size", "Disabled (Default)")
        if chunk_size != "Disabled (Default)":
            ydl_opts["http_chunk_size"] = chunk_size.replace(" MB", "M").replace(" KB", "K")

        socket_timeout = config_manager.get("socket_timeout", 20)
        ydl_opts["socket_timeout"] = socket_timeout

        container_choice = config_manager.get("default_video_container", "Auto (Default)").strip().lower()
        if container_choice and container_choice != "auto (default)":
            ydl_opts["merge_output_format"] = container_choice

        ffmpeg_path = config_manager.get("ffmpeg_path")
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        save_dir = config_manager.get("download_directory")
        ydl_opts["outtmpl"] = {"default": save_dir}

        if type_str == "Playlist":
            pass
        else:
            ydl_opts["noplaylist"] = True

        download_manager.add_task(url, title, ydl_opts, item.get("thumbnail_local_path"))
        self.main_window.switch_tab(1)  # Switch to Queue tab
        self._toast("success", "Download Started", f"Added '{title}' to queue.")

    def _remove_item(self, url: str):
        box = MessageBox(
            "Remove Item", "Are you sure you want to remove this item from your library?", self
        )
        if box.exec():
            library_manager.remove_item(url)
            self.refresh_library()

    @Slot()
    def _quick_add(self):
        url = sanitize_url(self.url_input.text())
        if not is_valid_url(url):
            self._toast("warning", "Invalid URL", "Please enter a valid HTTP or HTTPS URL.")
            return

        self.add_btn.setEnabled(False)
        self.add_btn.setText("Saving...")
        self.url_input.setEnabled(False)

        # Clear old analyzer
        if self.analyzer:
            self.analyzer.cancel()
            try:
                self.analyzer.analysis_completed.disconnect()
                self.analyzer.analysis_failed.disconnect()
            except RuntimeError:
                pass
            self.terminating_analyzers.add(self.analyzer)
            self.analyzer.finished.connect(
                lambda a=self.analyzer: self._handle_analyzer_terminated(a)
            )
            self.analyzer = None

        has_video = "v=" in url or "watch?" in url
        has_playlist = "list=" in url
        noplaylist = has_video and has_playlist and "index=" in url

        self.analyzer = VideoAnalyzer(url, noplaylist=noplaylist)
        self.analyzer.analysis_completed.connect(self._on_quick_add_success)
        self.analyzer.analysis_failed.connect(self._on_quick_add_failed)
        self.analyzer.start()

    def _handle_analyzer_terminated(self, analyzer):
        if analyzer in self.terminating_analyzers:
            self.terminating_analyzers.remove(analyzer)

    @Slot(dict)
    def _on_quick_add_success(self, info: dict):
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Save")
        self.url_input.setEnabled(True)

        url = info.get("webpage_url") or self.url_input.text().strip()
        title = info.get("title", "Unknown Title")
        uploader = info.get("uploader", "Unknown Channel")
        duration = (
            self.main_window.downloader_tab._format_duration(info.get("duration", 0))
            if info.get("duration")
            else "Unknown"
        )

        is_playlist = info.get("_type") == "playlist" or "entries" in info
        type_str = "Playlist" if is_playlist else "Video"

        if is_playlist:
            entries = info.get("entries", [])
            if entries is not None:
                if not isinstance(entries, list):
                    try:
                        entries = list(entries)
                    except Exception:
                        entries = []
            else:
                entries = []
            count = len(entries)
            if count == 0 and info.get("playlist_count"):
                count = info.get("playlist_count")
            duration = f"{count} items"

        thumb_path = info.get("thumbnail_local_path")

        success = library_manager.add_item(url, title, uploader, duration, type_str, thumb_path)
        if success:
            self.url_input.clear()
            self._toast("success", "Saved to Library", f"'{title}' was added to your library!")
            self.refresh_library()
        else:
            self._toast(
                "warning", "Already Saved", "This video/playlist is already in your library."
            )

    @Slot(str)
    def _on_quick_add_failed(self, error: str):
        url = self.analyzer.url
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Save")
        self.url_input.setEnabled(True)

        box = MessageBox(
            "Metadata Fetch Failed",
            f"Could not retrieve video metadata: {error}\n\n"
            "Do you still want to save the URL to your library?",
            self,
        )
        if box.exec():
            success = library_manager.add_item(
                url=url,
                title=url,
                uploader="Unknown",
                duration="Unknown",
                type_str="Video",
                thumbnail_path=None,
            )
            if success:
                self.url_input.clear()
                self.refresh_library()
            else:
                self._toast("warning", "Already Saved", "This URL is already in your library.")
