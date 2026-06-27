import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QAbstractItemView
)
from PySide6.QtGui import QPixmap
from ..utils.library_manager import library_manager
from ..yt_dlp_worker import VideoAnalyzer
from ..utils.logger import get_logger

logger = get_logger("library_tab")

class LibraryTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.analyzer = None
        self.terminating_analyzers = set()
        
        self._init_ui()
        self.refresh_library()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Quick Add Section
        add_frame = QFrame()
        add_frame.setObjectName("cardFrame")
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 12, 12, 12)
        add_layout.setSpacing(10)

        add_layout.addWidget(QLabel("Quick Save URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video or playlist URL to save for later...")
        add_layout.addWidget(self.url_input)

        self.add_btn = QPushButton("Save")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self._quick_add)
        add_layout.addWidget(self.add_btn)

        layout.addWidget(add_frame)

        # 2. Header Status
        header_row = QHBoxLayout()
        self.count_label = QLabel("Saved Items: 0")
        self.count_label.setObjectName("sectionHeader")
        header_row.addWidget(self.count_label)
        header_row.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMinimumHeight(24)
        self.refresh_btn.clicked.connect(self.refresh_library)
        header_row.addWidget(self.refresh_btn)
        
        layout.addLayout(header_row)

        # 3. Library Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Thumbnail", "Title & Channel", "Details", "Date Added", "Actions"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Header configuration
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)       # Thumbnail
        header.setSectionResizeMode(1, QHeaderView.Stretch)     # Title & Channel
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Details
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Date Added
        header.setSectionResizeMode(4, QHeaderView.Fixed)       # Actions
        
        self.table.setColumnWidth(0, 90)   # Thumbnail
        self.table.setColumnWidth(4, 260)  # Actions (Load, Download, Remove)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)

    def refresh_library(self):
        self.table.setRowCount(0)
        items = library_manager.items
        self.count_label.setText(f"Saved Items: {len(items)}")
        
        for row, item in enumerate(items):
            self.table.insertRow(row)
            
            # Column 0: Thumbnail
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setFixedSize(80, 45)
            self._set_thumbnail_on_label(thumb_label, item.get('thumbnail_local_path'))
            self.table.setCellWidget(row, 0, thumb_label)
            
            # Column 1: Title & Channel
            title = item.get('title', 'Unknown Title')
            uploader = item.get('uploader', 'Unknown Channel')
            title_text = f"<b>{title}</b><br/><font color='#a1a1aa' size='2'>{uploader}</font>"
            
            title_label = QLabel()
            title_label.setText(title_text)
            title_label.setTextFormat(Qt.RichText)
            title_label.setWordWrap(True)
            title_label.setStyleSheet("padding: 4px;")
            self.table.setCellWidget(row, 1, title_label)
            
            # Column 2: Details
            type_str = item.get('type', 'Video')
            duration = item.get('duration', 'Unknown')
            details_text = f"{type_str}\n({duration})"
            details_item = QTableWidgetItem(details_text)
            details_item.setFlags(details_item.flags() & ~Qt.ItemIsEditable)
            details_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 2, details_item)
            
            # Column 3: Date Added
            date_item = QTableWidgetItem(item.get('added_at', 'Unknown'))
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
            date_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 3, date_item)
            
            # Column 4: Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            
            load_btn = QPushButton("Configure")
            load_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            load_btn.setMinimumHeight(24)
            load_btn.clicked.connect(lambda _, url=item['url']: self._load_item(url))
            
            dl_btn = QPushButton("Quick DL")
            dl_btn.setObjectName("primaryButton")
            dl_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            dl_btn.setMinimumHeight(24)
            dl_btn.clicked.connect(lambda _, it=item: self._quick_download_item(it))
            
            remove_btn = QPushButton("✕")
            remove_btn.setStyleSheet("padding: 0px; font-weight: bold; font-size: 14px;")
            remove_btn.setFixedSize(24, 24)
            remove_btn.clicked.connect(lambda _, url=item['url']: self._remove_item(url))
            
            actions_layout.addWidget(load_btn)
            actions_layout.addWidget(dl_btn)
            actions_layout.addWidget(remove_btn)
            self.table.setCellWidget(row, 4, actions_widget)

    def _set_thumbnail_on_label(self, label: QLabel, path: str):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            label.setPixmap(pixmap.scaled(
                label.width(), 
                label.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))
        else:
            label.setText("No Preview")

    def _load_item(self, url: str):
        """Switch to Downloader tab and analyze the URL."""
        self.main_window.downloader_tab.url_input.setText(url)
        self.main_window.switch_tab(0) # Downloader is 0
        self.main_window.downloader_tab._start_analysis()

    def _quick_download_item(self, item: dict):
        """Immediately add the item to the download queue using default options."""
        url = item['url']
        title = item['title']
        type_str = item.get('type', 'Video')
        
        from ..config import config_manager
        from ..download_manager import download_manager
        
        ydl_opts = {
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo+bestaudio/best',
        }
        
        ffmpeg_path = config_manager.get("ffmpeg_path")
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
        save_dir = config_manager.get("download_directory")
        ydl_opts['outtmpl'] = {'default': save_dir}
        
        if type_str == "Playlist":
            pass
        else:
            ydl_opts['noplaylist'] = True

        download_manager.add_task(url, title, ydl_opts, item.get('thumbnail_local_path'))
        self.main_window.switch_tab(1) # Switch to Queue tab
        QMessageBox.information(self, "Download Started", f"Added '{title}' to queue.")

    def _remove_item(self, url: str):
        reply = QMessageBox.question(
            self, "Remove Item",
            "Are you sure you want to remove this item from your library?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            library_manager.remove_item(url)
            self.refresh_library()

    @Slot()
    def _quick_add(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL first.")
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
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
            self.analyzer.finished.connect(lambda a=self.analyzer: self._handle_analyzer_terminated(a))
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
        
        url = info.get('webpage_url') or self.url_input.text().strip()
        title = info.get('title', 'Unknown Title')
        uploader = info.get('uploader', 'Unknown Channel')
        duration = self.main_window.downloader_tab._format_duration(info.get('duration', 0)) if info.get('duration') else "Unknown"
        
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        type_str = "Playlist" if is_playlist else "Video"
        
        if is_playlist:
            entries = info.get('entries', [])
            if entries is not None:
                if not isinstance(entries, list):
                    try:
                        entries = list(entries)
                    except Exception:
                        entries = []
            else:
                entries = []
            count = len(entries)
            if count == 0 and info.get('playlist_count'):
                count = info.get('playlist_count')
            duration = f"{count} items"
            
        thumb_path = info.get('thumbnail_local_path')
        
        success = library_manager.add_item(url, title, uploader, duration, type_str, thumb_path)
        if success:
            self.url_input.clear()
            QMessageBox.information(self, "Saved to Library", f"Successfully saved '{title}' to your library!")
            self.refresh_library()
        else:
            QMessageBox.warning(self, "Already Saved", "This video/playlist is already saved in your library.")

    @Slot(str)
    def _on_quick_add_failed(self, error: str):
        url = self.analyzer.url
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Save")
        self.url_input.setEnabled(True)
        
        reply = QMessageBox.question(
            self, "Metadata Fetch Failed",
            f"Could not retrieve video metadata: {error}\n\nDo you still want to save the URL to your library?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            success = library_manager.add_item(
                url=url,
                title=url,
                uploader="Unknown",
                duration="Unknown",
                type_str="Video",
                thumbnail_path=None
            )
            if success:
                self.url_input.clear()
                self.refresh_library()
            else:
                QMessageBox.warning(self, "Already Saved", "This URL is already saved in your library.")
