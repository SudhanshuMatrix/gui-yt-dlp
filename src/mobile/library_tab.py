from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.library_manager import library_manager
from ..utils.logger import get_logger
from ..utils.url_sanitizer import is_valid_url, sanitize_url
from ..yt_dlp_worker import VideoAnalyzer

logger = get_logger("mobile_library_tab")


class LibraryRowWidget(QFrame):
    def __init__(self, item: dict, parent_tab: "LibraryTab"):
        super().__init__()
        self.item = item
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_label = QLabel(item.get("title", "Unknown"))
        title_label.setObjectName("cardTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        meta_label = QLabel(f"{item.get('uploader', 'Unknown')} · {item.get('type', 'Video')}")
        meta_label.setObjectName("mutedLabel")
        layout.addWidget(meta_label)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Open")
        load_btn.clicked.connect(lambda: parent_tab.load_item(item["url"]))
        btn_row.addWidget(load_btn)

        dl_btn = QPushButton("Quick DL")
        dl_btn.setObjectName("primaryButton")
        dl_btn.clicked.connect(lambda: parent_tab.quick_download(item))
        btn_row.addWidget(dl_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(lambda: parent_tab.remove_item(item["url"]))
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)


class LibraryTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.analyzer: VideoAnalyzer | None = None

        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Library")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        add_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL to save for later...")
        self.url_input.setMinimumHeight(44)
        add_row.addWidget(self.url_input, 1)
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._quick_add)
        add_row.addWidget(self.save_btn)
        layout.addLayout(add_row)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        self.empty_label = QLabel("Nothing saved yet.")
        self.empty_label.setObjectName("mutedLabel")
        layout.addWidget(self.empty_label)

    def refresh(self):
        self.list_widget.clear()
        items = library_manager.items
        self.empty_label.setVisible(len(items) == 0)
        for item in items:
            list_item = QListWidgetItem(self.list_widget)
            row = LibraryRowWidget(item, self)
            list_item.setSizeHint(row.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, row)

    def load_item(self, url: str):
        self.main_window.downloader_tab.url_input.setText(url)
        self.main_window.switch_tab(0)
        self.main_window.downloader_tab._start_analysis()

    def quick_download(self, item: dict):
        from ..config import config_manager
        from ..download_manager import download_manager

        opts = {
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "format": "best/bestvideo+bestaudio",
            "outtmpl": {"default": config_manager.get("download_directory")},
        }
        if item.get("type") != "Playlist":
            opts["noplaylist"] = True

        download_manager.add_task(
            item["url"], item["title"], opts, item.get("thumbnail_local_path")
        )
        self.main_window.switch_tab(1)
        QMessageBox.information(self, "Queued", f"Added '{item['title']}' to the queue.")

    def remove_item(self, url: str):
        reply = QMessageBox.question(
            self,
            "Remove Item",
            "Remove this item from your library?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            library_manager.remove_item(url)
            self.refresh()

    @Slot()
    def _quick_add(self):
        url = sanitize_url(self.url_input.text())
        if not is_valid_url(url):
            QMessageBox.warning(self, "Invalid URL", "Enter a valid http(s) URL.")
            return

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving...")

        if self.analyzer:
            self.analyzer.cancel()
            try:
                self.analyzer.analysis_completed.disconnect()
                self.analyzer.analysis_failed.disconnect()
            except RuntimeError:
                pass

        self.analyzer = VideoAnalyzer(url)
        self.analyzer.analysis_completed.connect(self._on_analysis_success)
        self.analyzer.analysis_failed.connect(self._on_analysis_failed)
        self.analyzer.start()

    @Slot(dict)
    def _on_analysis_success(self, info: dict):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save")

        url = info.get("webpage_url") or self.url_input.text().strip()
        title = info.get("title", "Unknown Title")
        uploader = info.get("uploader", "Unknown")
        is_playlist = info.get("_type") == "playlist" or "entries" in info
        type_str = "Playlist" if is_playlist else "Video"

        success = library_manager.add_item(
            url, title, uploader, "", type_str, info.get("thumbnail_local_path")
        )
        if success:
            self.url_input.clear()
            self.refresh()
        else:
            QMessageBox.warning(self, "Already Saved", "This URL is already in your library.")

    @Slot(str)
    def _on_analysis_failed(self, error: str):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save")
        QMessageBox.warning(self, "Failed", f"Could not fetch info: {error}")
