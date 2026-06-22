import os
from typing import Any, Dict, List, Optional, Tuple
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QComboBox, QCheckBox, QGroupBox, QFileDialog,
    QMessageBox, QScrollArea, QSizePolicy, QProgressBar, QSpinBox
)
from PySide6.QtGui import QPixmap, QGuiApplication
from ..yt_dlp_worker import VideoAnalyzer, PlaylistFirstVideoAnalyzer
from ..download_manager import download_manager
from ..config import config_manager
from ..utils.logger import get_logger

logger = get_logger("downloader_tab")

class DownloaderTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.current_analysis: Dict[str, Any] = {}
        self.video_formats: List[Dict[str, Any]] = []
        self.audio_formats: List[Dict[str, Any]] = []
        self.analyzer: VideoAnalyzer = None
        self.first_video_analyzer: Optional[PlaylistFirstVideoAnalyzer] = None
        self.active_download_task_id = None
        self.terminating_analyzers = set()

        self._init_ui()
        download_manager.task_updated.connect(self._on_task_updated_downloader)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. URL Input Section
        url_section_layout = QVBoxLayout()
        url_section_layout.setSpacing(6)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube or other video/playlist URL...")
        self.url_input.setMinimumHeight(40)
        self.url_input.textChanged.connect(self._on_url_changed)
        input_layout.addWidget(self.url_input)
        
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setMinimumHeight(40)
        self.paste_btn.clicked.connect(self._paste_clipboard)
        input_layout.addWidget(self.paste_btn)
        
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.setMinimumHeight(40)
        self.analyze_btn.clicked.connect(self._start_analysis)
        input_layout.addWidget(self.analyze_btn)
        
        url_section_layout.addLayout(input_layout)
        
        # Checkbox for combined links
        self.noplaylist_check = QCheckBox("Ignore playlist context and download only the single video")
        self.noplaylist_check.setVisible(False)
        url_section_layout.addWidget(self.noplaylist_check)
        
        layout.addLayout(url_section_layout)

        # 2. Main content area (Scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(16)
        
        # Result Card (Frame container)
        self.result_card = QFrame()
        self.result_card.setObjectName("cardFrame")
        self.result_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.result_card_layout = QVBoxLayout(self.result_card)
        self.result_card_layout.setContentsMargins(16, 16, 16, 16)
        self.result_card_layout.setSpacing(16)
        
        # Result Header: Thumbnail & Meta Info
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)
        
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(240, 135) # 16:9
        self.thumb_label.setStyleSheet("background-color: #000000; border-radius: 4px;")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        meta_layout.addWidget(self.thumb_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        self.title_label = QLabel("Title")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)
        
        self.uploader_label = QLabel("Uploader: ")
        self.uploader_label.setObjectName("subtitleLabel")
        info_layout.addWidget(self.uploader_label)
        
        self.duration_label = QLabel("Duration: ")
        self.duration_label.setObjectName("subtitleLabel")
        info_layout.addWidget(self.duration_label)
        
        self.type_label = QLabel("Type: Video")
        self.type_label.setObjectName("subtitleLabel")
        info_layout.addWidget(self.type_label)
        
        info_layout.addStretch()
        meta_layout.addLayout(info_layout)
        self.result_card_layout.addLayout(meta_layout)
        
        # Download Config Group
        self.config_group = QGroupBox("Download Options")
        self.config_group_layout = QVBoxLayout(self.config_group)
        self.config_group_layout.setSpacing(12)
        
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Download Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Best Quality (Video + Audio combined)",
            "Video Only",
            "Audio Only (MP3 Conversion)",
            "Custom Formats Selection"
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.setStretch(1, 1)
        self.config_group_layout.addLayout(mode_layout)
        
        # Custom Formats Frame (Shown conditionally)
        self.custom_formats_frame = QFrame()
        self.custom_formats_frame.setVisible(False)
        custom_layout = QVBoxLayout(self.custom_formats_frame)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(10)
        
        vid_fmt_layout = QHBoxLayout()
        vid_fmt_layout.addWidget(QLabel("Video Format:"))
        self.video_format_combo = QComboBox()
        vid_fmt_layout.addWidget(self.video_format_combo)
        vid_fmt_layout.setStretch(1, 1)
        custom_layout.addLayout(vid_fmt_layout)
        
        aud_fmt_layout = QHBoxLayout()
        aud_fmt_layout.addWidget(QLabel("Audio Format:"))
        self.audio_format_combo = QComboBox()
        aud_fmt_layout.addWidget(self.audio_format_combo)
        aud_fmt_layout.setStretch(1, 1)
        # Wrap in a widget so we can hide it independently (e.g. in Video Only mode)
        self.audio_format_row = QWidget()
        self.audio_format_row.setLayout(aud_fmt_layout)
        custom_layout.addWidget(self.audio_format_row)
        
        self.config_group_layout.addWidget(self.custom_formats_frame)
        
        # Audio Quality Frame (Shown for MP3 mode)
        self.audio_quality_frame = QFrame()
        self.audio_quality_frame.setVisible(False)
        aq_layout = QHBoxLayout(self.audio_quality_frame)
        aq_layout.setContentsMargins(0, 0, 0, 0)
        aq_layout.addWidget(QLabel("MP3 Quality (Bitrate):"))
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["320 kbps (High)", "256 kbps", "192 kbps (Medium)", "128 kbps (Low)"])
        self.audio_quality_combo.setCurrentIndex(2) # Default to 192
        aq_layout.addWidget(self.audio_quality_combo)
        aq_layout.setStretch(1, 1)
        self.config_group_layout.addWidget(self.audio_quality_frame)

        # Playlist Options Frame (Shown only for playlists)
        self.playlist_options_frame = QFrame()
        self.playlist_options_frame.setVisible(False)
        self.playlist_options_frame.setStyleSheet("""
            QFrame {
                border: 1px dashed #3f3f46;
                border-radius: 6px;
                background-color: #18181b;
            }
        """)
        playlist_layout = QVBoxLayout(self.playlist_options_frame)
        playlist_layout.setContentsMargins(10, 10, 10, 10)
        playlist_layout.setSpacing(8)
        
        self.playlist_range_check = QCheckBox("Limit download to specific playlist items")
        self.playlist_range_check.stateChanged.connect(self._on_playlist_range_checked)
        playlist_layout.addWidget(self.playlist_range_check)
        
        # Range widgets layout
        self.playlist_range_widgets = QWidget()
        range_widgets_layout = QVBoxLayout(self.playlist_range_widgets)
        range_widgets_layout.setContentsMargins(0, 0, 0, 0)
        range_widgets_layout.setSpacing(6)
        
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Start Index:"))
        self.playlist_start_spin = QSpinBox()
        self.playlist_start_spin.setRange(1, 99999)
        self.playlist_start_spin.setValue(1)
        spin_layout.addWidget(self.playlist_start_spin)
        
        spin_layout.addWidget(QLabel("End Index:"))
        self.playlist_end_spin = QSpinBox()
        self.playlist_end_spin.setRange(1, 99999)
        self.playlist_end_spin.setValue(1)
        spin_layout.addWidget(self.playlist_end_spin)
        range_widgets_layout.addLayout(spin_layout)
        
        items_layout = QHBoxLayout()
        items_layout.addWidget(QLabel("Advanced Selection (e.g. 1,3,5-10):"))
        self.playlist_items_input = QLineEdit()
        self.playlist_items_input.setPlaceholderText("Leave empty to use start/end index")
        items_layout.addWidget(self.playlist_items_input)
        range_widgets_layout.addLayout(items_layout)
        
        playlist_layout.addWidget(self.playlist_range_widgets)
        self.playlist_range_widgets.setEnabled(False) # disabled by default
        
        self.config_group_layout.addWidget(self.playlist_options_frame)

        # Subtitles row
        sub_layout = QHBoxLayout()
        self.subtitles_check = QCheckBox("Download Subtitles")
        self.subtitles_check.stateChanged.connect(self._on_subs_checked)
        sub_layout.addWidget(self.subtitles_check)
        
        self.subtitle_lang_combo = QComboBox()
        self.subtitle_lang_combo.setEnabled(False)
        self.subtitle_lang_combo.addItems(["en", "es", "fr", "de", "it", "ja", "ko", "zh"])
        sub_layout.addWidget(self.subtitle_lang_combo)
        
        self.embed_subs_check = QCheckBox("Embed Subtitles in Video")
        self.embed_subs_check.setEnabled(False)
        sub_layout.addWidget(self.embed_subs_check)
        sub_layout.addStretch()
        self.config_group_layout.addLayout(sub_layout)

        # Other post-processing options
        opts_layout = QHBoxLayout()
        self.embed_thumb_check = QCheckBox("Embed Thumbnail")
        self.embed_thumb_check.setChecked(config_manager.get("embed_thumbnail", False))
        opts_layout.addWidget(self.embed_thumb_check)
        
        self.add_metadata_check = QCheckBox("Add Metadata / Tags")
        self.add_metadata_check.setChecked(config_manager.get("add_metadata", False))
        opts_layout.addWidget(self.add_metadata_check)
        opts_layout.addStretch()
        self.config_group_layout.addLayout(opts_layout)

        # Output folder row
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Save to:"))
        self.output_path_input = QLineEdit(config_manager.get("download_directory"))
        output_layout.addWidget(self.output_path_input)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_folder)
        output_layout.addWidget(self.browse_btn)
        self.config_group_layout.addLayout(output_layout)

        self.result_card_layout.addWidget(self.config_group)

        # 3. Progress Container (shown only during active download started from this tab)
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("cardFrame")
        self.progress_frame.setVisible(False)
        
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(12, 12, 12, 12)
        progress_layout.setSpacing(10)
        
        self.progress_title = QLabel("Downloading...")
        self.progress_title.setObjectName("sectionHeader")
        progress_layout.addWidget(self.progress_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        progress_layout.addWidget(self.progress_bar)
        
        prog_info_layout = QHBoxLayout()
        self.progress_speed_label = QLabel("Speed: 0 B/s")
        self.progress_speed_label.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        prog_info_layout.addWidget(self.progress_speed_label)
        
        self.progress_eta_label = QLabel("ETA: Unknown")
        self.progress_eta_label.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        prog_info_layout.addWidget(self.progress_eta_label)
        
        self.progress_size_label = QLabel("Size: 0 B / Unknown")
        self.progress_size_label.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        prog_info_layout.addWidget(self.progress_size_label)
        prog_info_layout.addStretch()
        progress_layout.addLayout(prog_info_layout)
        
        prog_btns_layout = QHBoxLayout()
        prog_btns_layout.addStretch()
        
        self.progress_pause_btn = QPushButton("Pause")
        self.progress_pause_btn.clicked.connect(self._toggle_pause_active_download)
        prog_btns_layout.addWidget(self.progress_pause_btn)
        
        self.progress_cancel_btn = QPushButton("Cancel")
        self.progress_cancel_btn.setObjectName("dangerButton")
        self.progress_cancel_btn.clicked.connect(self._cancel_active_download)
        prog_btns_layout.addWidget(self.progress_cancel_btn)
        
        self.progress_done_btn = QPushButton("Done")
        self.progress_done_btn.setObjectName("primaryButton")
        self.progress_done_btn.clicked.connect(self._reset_downloader)
        self.progress_done_btn.setVisible(False)
        prog_btns_layout.addWidget(self.progress_done_btn)
        
        progress_layout.addLayout(prog_btns_layout)
        self.result_card_layout.addWidget(self.progress_frame)

        # ── Pre-check progress frame ─────────────────────────────────
        self.precheck_frame = QFrame()
        self.precheck_frame.setObjectName("cardFrame")
        self.precheck_frame.setVisible(False)
        precheck_vlay = QVBoxLayout(self.precheck_frame)
        precheck_vlay.setContentsMargins(14, 12, 14, 12)
        precheck_vlay.setSpacing(8)

        precheck_hdr = QLabel("🔍  Checking format availability for each video...")
        precheck_hdr.setObjectName("sectionHeader")
        precheck_vlay.addWidget(precheck_hdr)

        self.precheck_bar = QProgressBar()
        self.precheck_bar.setRange(0, 100)
        self.precheck_bar.setValue(0)
        self.precheck_bar.setFixedHeight(14)
        precheck_vlay.addWidget(self.precheck_bar)

        precheck_info_row = QHBoxLayout()
        self.precheck_count_label = QLabel("0 / 0")
        self.precheck_count_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        precheck_info_row.addWidget(self.precheck_count_label)
        self.precheck_title_label = QLabel("")
        self.precheck_title_label.setStyleSheet("color: #71717a; font-size: 11px;")
        self.precheck_title_label.setWordWrap(True)
        precheck_info_row.addWidget(self.precheck_title_label, 1)
        precheck_vlay.addLayout(precheck_info_row)

        cancel_precheck_btn = QPushButton("Cancel")
        cancel_precheck_btn.setObjectName("dangerButton")
        cancel_precheck_btn.clicked.connect(self._cancel_precheck)
        precheck_vlay.addWidget(cancel_precheck_btn, alignment=Qt.AlignRight)

        self.result_card_layout.addWidget(self.precheck_frame)

        # ── Bottom action buttons ────────────────────────────────────
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()

        self.add_queue_btn = QPushButton("Add to Queue")
        self.add_queue_btn.setMinimumHeight(36)
        self.add_queue_btn.clicked.connect(self._add_to_queue)
        btns_layout.addWidget(self.add_queue_btn)

        self.download_now_btn = QPushButton("Download Now")
        self.download_now_btn.setObjectName("primaryButton")
        self.download_now_btn.setMinimumHeight(36)
        self.download_now_btn.clicked.connect(self._download_now)
        btns_layout.addWidget(self.download_now_btn)

        self.result_card_layout.addLayout(btns_layout)
        self.scroll_layout.addWidget(self.result_card)
        self.result_card.setVisible(False)
        
        # Centered Welcome / Status Label
        self.status_label = QLabel("Enter a URL above to analyze and download videos.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #71717a; font-size: 14px; margin-top: 100px;")
        self.scroll_layout.addWidget(self.status_label)

        self.scroll_area.setWidget(scroll_content)
        layout.addWidget(self.scroll_area)

    @Slot()
    def _paste_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        self.url_input.setText(clipboard.text())

    @Slot()
    def _browse_folder(self):
        current_dir = self.output_path_input.text() or config_manager.get("download_directory")
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", current_dir)
        if folder:
            self.output_path_input.setText(folder)

    @Slot(int)
    def _on_subs_checked(self, state: int):
        is_checked = state == Qt.Checked.value
        self.subtitle_lang_combo.setEnabled(is_checked)
        self.embed_subs_check.setEnabled(is_checked)

    @Slot(int)
    def _on_mode_changed(self, index: int):
        # Index: 0 = Best, 1 = Video Only, 2 = Audio Only, 3 = Custom
        # Show format combos for Video Only (video only) and Custom (video + audio)
        self.custom_formats_frame.setVisible(index in (1, 3))
        self.audio_format_row.setVisible(index == 3)   # audio row only needed for Custom
        self.audio_quality_frame.setVisible(index == 2)

        # In Audio Only mode disable subtitles
        self.subtitles_check.setEnabled(index != 2)
        if index == 2:
            self.subtitles_check.setChecked(False)

        # For playlists: fetch formats from first video when user picks Video Only or Custom
        if index in (1, 3) and self.current_analysis:
            is_playlist = (
                self.current_analysis.get('_type') == 'playlist'
                or 'entries' in self.current_analysis
            )
            if is_playlist:
                self._load_first_video_formats()

    @Slot()
    def _start_analysis(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        self.status_label.setText("Fetching metadata from video...")
        self.status_label.setVisible(True)
        self.result_card.setVisible(False)
        
        # Clean old analyzer
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
            
        noplaylist = self.noplaylist_check.isVisible() and self.noplaylist_check.isChecked()
        self.analyzer = VideoAnalyzer(url, noplaylist=noplaylist)
        self.analyzer.analysis_completed.connect(self._on_analysis_success)
        self.analyzer.analysis_failed.connect(self._on_analysis_failed)
        self.analyzer.start()

    def _handle_analyzer_terminated(self, analyzer):
        if analyzer in self.terminating_analyzers:
            self.terminating_analyzers.remove(analyzer)
            logger.info("Cleaned up terminating analyzer/precheck thread.")

    @Slot(dict)
    def _on_analysis_success(self, info: dict):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        self.status_label.setVisible(False)
        
        self.current_analysis = info
        
        # Title & Meta Info
        self.title_label.setText(info.get('title', 'Unknown Title'))
        self.uploader_label.setText(f"Uploader: {info.get('uploader', 'Unknown')}")
        
        duration = info.get('duration', 0)
        if duration:
            self.duration_label.setText(f"Duration: {self._format_duration(duration)}")
            self.duration_label.setVisible(True)
        else:
            self.duration_label.setVisible(False)
            
        # Is playlist or single video?
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
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
            # Store materialised list back so _get_playlist_entries() can reuse it
            info['_entries_list'] = entries
            count = len(entries)
            if count == 0 and info.get('playlist_count'):
                count = info.get('playlist_count')

            self.type_label.setText(f"Type: Playlist ({count} items)")
            self.mode_combo.setCurrentIndex(0)
            self.mode_combo.setEnabled(True)
            self._on_mode_changed(0)   # reset format frames

            self.playlist_options_frame.setVisible(True)
            self.playlist_range_check.setChecked(False)
            if count > 0:
                self.playlist_start_spin.setRange(1, count)
                self.playlist_start_spin.setValue(1)
                self.playlist_end_spin.setRange(1, count)
                self.playlist_end_spin.setValue(count)
            else:
                self.playlist_start_spin.setRange(1, 99999)
                self.playlist_start_spin.setValue(1)
                self.playlist_end_spin.setRange(1, 99999)
                self.playlist_end_spin.setValue(10)
        else:
            self.type_label.setText("Type: Single Video")
            self.mode_combo.setEnabled(True)
            self._parse_formats(info)
            self.playlist_options_frame.setVisible(False)

        # Set Thumbnail
        thumb_path = info.get('thumbnail_local_path')
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            self.thumb_label.setPixmap(pixmap.scaled(
                self.thumb_label.width(), 
                self.thumb_label.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))
        else:
            self.thumb_label.setText("No Preview")
            
        # Display settings
        self.result_card.setVisible(True)

    @Slot(str)
    def _on_analysis_failed(self, error: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        self.status_label.setText("Analysis failed. See error details.")
        QMessageBox.critical(self, "Analysis Failed", f"Could not analyze URL: {error}")

    def _parse_formats(self, info: dict):
        self.video_formats = []
        self.audio_formats = []
        
        formats = info.get('formats', [])
        for f in formats:
            f_id = f.get('format_id', '')
            if not f_id:
                continue
                
            ext = f.get('ext', '')
            vcodec = str(f.get('vcodec') or 'none').lower()
            acodec = str(f.get('acodec') or 'none').lower()

            is_video = vcodec != 'none'
            is_audio = acodec != 'none'

            if is_video:
                height = f.get('height', 0)
                fps = f.get('fps')
                fps_str = f" {fps}fps" if fps and fps > 30 else ""

                if is_audio:
                    res_desc = f"{height}p" if height else "Video+Audio"
                    desc = f"{res_desc}{fps_str} ({ext}) [Combined]"
                else:
                    res_desc = f"{height}p" if height else "Video Only"
                    desc = f"{res_desc}{fps_str} ({ext})"

                self.video_formats.append({
                    'id': f_id,
                    'ext': ext,
                    'height': height,
                    'is_combined': is_audio,
                    'desc': desc
                })
            elif is_audio:
                abr = f.get('abr') or f.get('tbr') or 0
                abr_desc = f"{int(abr)}kbps" if abr > 0 else "Audio Only"
                self.audio_formats.append({
                    'id': f_id,
                    'ext': ext,
                    'abr': abr,
                    'desc': f"{abr_desc} ({ext})"
                })

        # Sort video formats by height (descending)
        self.video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        # Sort audio formats by bitrate (descending)
        self.audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)

        # Update combo boxes
        self.video_format_combo.clear()
        for f in self.video_formats:
            self.video_format_combo.addItem(f['desc'], f['id'])
            
        self.audio_format_combo.clear()
        for f in self.audio_formats:
            self.audio_format_combo.addItem(f['desc'], f['id'])

    def _build_ydl_opts(self) -> Dict[str, Any]:
        """Construct the options dict for yt-dlp based on GUI selections."""
        opts: Dict[str, Any] = {
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
        }

        mode_idx = self.mode_combo.currentIndex()
        
        # Check if we should ignore playlist
        if self.noplaylist_check.isVisible() and self.noplaylist_check.isChecked():
            opts['noplaylist'] = True
            is_playlist = False
        else:
            is_playlist = self.current_analysis.get('_type') == 'playlist' or 'entries' in self.current_analysis

        if is_playlist:
            if mode_idx == 0:  # Best Quality
                opts['format'] = 'bestvideo+bestaudio/best'
            elif mode_idx == 1:  # Video Only — use selected format if available
                vid_id = self.video_format_combo.currentData()
                opts['format'] = vid_id if vid_id else 'bestvideo/best'
            elif mode_idx == 2:  # Audio Only (MP3)
                opts['format'] = 'bestaudio/best'
                bitrate_str = self.audio_quality_combo.currentText().split(" ")[0]
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate_str,
                }]
            else:  # Custom — format is handled by the precheck+fallback flow
                video_id = self.video_format_combo.currentData()
                audio_id = self.audio_format_combo.currentData()
                selected_video_is_combined = any(
                    f['id'] == video_id and f.get('is_combined') for f in self.video_formats
                )
                if video_id and audio_id and not selected_video_is_combined:
                    opts['format'] = f"{video_id}+{audio_id}/best"
                elif video_id:
                    opts['format'] = video_id
                else:
                    opts['format'] = 'bestvideo+bestaudio/best'
            # Range configurations
            if self.playlist_range_check.isChecked():
                items_spec = self.playlist_items_input.text().strip()
                if items_spec:
                    opts['playlist_items'] = items_spec
                else:
                    opts['playliststart'] = self.playlist_start_spin.value()
                    opts['playlistend'] = self.playlist_end_spin.value()
        else:
            if mode_idx == 0: # Best Quality
                opts['format'] = 'bestvideo+bestaudio/best'
            elif mode_idx == 1: # Video Only
                # Download best video format only
                opts['format'] = 'bestvideo/best'
            elif mode_idx == 2: # Audio Only (MP3 conversion)
                opts['format'] = 'bestaudio/best'
                # Setup MP3 post processor
                bitrate_str = self.audio_quality_combo.currentText().split(" ")[0] # e.g. "192"
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate_str,
                }]
            elif mode_idx == 3: # Custom Format
                video_id = self.video_format_combo.currentData()
                audio_id = self.audio_format_combo.currentData()
                
                # Check if selected video format already contains audio (is combined)
                selected_video_is_combined = False
                for f in self.video_formats:
                    if f['id'] == video_id:
                        selected_video_is_combined = f.get('is_combined', False)
                        break
                
                if video_id and audio_id and not selected_video_is_combined:
                    # Merge them
                    opts['format'] = f"{video_id}+{audio_id}/best"
                elif video_id:
                    opts['format'] = video_id
                elif audio_id:
                    opts['format'] = audio_id

        # Subtitles options
        if self.subtitles_check.isChecked() and mode_idx != 2:
            lang = self.subtitle_lang_combo.currentText()
            opts['writesubtitles'] = True
            opts['writeautomaticsubtitles'] = True
            opts['subtitleslangs'] = [lang]
            if self.embed_subs_check.isChecked():
                if 'postprocessors' not in opts:
                    opts['postprocessors'] = []
                opts['postprocessors'].append({
                    'key': 'FFmpegEmbedSubtitle',
                    'already_have_subtitle': False,
                })

        # Thumbnail embedding
        if self.embed_thumb_check.isChecked():
            opts['writethumbnail'] = True
            if 'postprocessors' not in opts:
                opts['postprocessors'] = []
            opts['postprocessors'].append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            })

        # Metadata tags embedding
        if self.add_metadata_check.isChecked():
            if 'postprocessors' not in opts:
                opts['postprocessors'] = []
            opts['postprocessors'].append({
                'key': 'FFmpegMetadata',
                'add_chapters': True,
            })

        # Set output template directory
        save_dir = self.output_path_input.text().strip() or config_manager.get("download_directory")
        opts['outtmpl'] = {'default': save_dir}

        return opts

    @Slot()
    def _add_to_queue(self):
        if not self.current_analysis:
            return
        if self._is_playlist():
            self._add_playlist_to_queue('queue')
        else:
            url = self.current_analysis.get('webpage_url') or self.url_input.text().strip()
            title = self.current_analysis.get('title', 'Unknown Title')
            thumb_path = self.current_analysis.get('thumbnail_local_path')
            ydl_opts = self._build_ydl_opts()
            download_manager.add_task(url, title, ydl_opts, thumb_path)
            self.url_input.clear()
            self.result_card.setVisible(False)
            self.status_label.setText("Added to Queue. Enter another URL to analyze.")
            self.status_label.setVisible(True)

    @Slot()
    def _download_now(self):
        if not self.current_analysis:
            return
        if self._is_playlist():
            self._add_playlist_to_queue('download')
        else:
            self._start_download_now_task(
                self.current_analysis.get('webpage_url') or self.url_input.text().strip(),
                self.current_analysis.get('title', 'Unknown Title'),
                self.current_analysis.get('thumbnail_local_path'),
                self._build_ydl_opts()
            )

    @Slot(str, dict)
    def _on_task_updated_downloader(self, task_id: str, data: dict):
        if task_id != self.active_download_task_id:
            return
            
        # Update progress bar
        if 'progress' in data:
            self.progress_bar.setValue(int(data['progress']))
            
        # Update sizes
        if 'downloaded' in data or 'total' in data:
            task = download_manager.tasks.get(task_id, {})
            self.progress_size_label.setText(f"{task.get('downloaded', '0 B')} / {task.get('total', 'Unknown')}")
            
        # Update speed
        if 'speed' in data:
            self.progress_speed_label.setText(f"Speed: {data['speed']}")
            
        # Update ETA / status string
        if 'eta' in data:
            self.progress_eta_label.setText(f"ETA: {data['eta']}")
            
        # Update status
        if 'status' in data:
            status = data['status']
            if status == 'Downloading':
                self.progress_title.setText("Downloading Video/Audio...")
                self.progress_pause_btn.setText("Pause")
                self.progress_pause_btn.setVisible(True)
            elif status == 'Paused':
                self.progress_title.setText("Paused")
                self.progress_pause_btn.setText("Resume")
                self.progress_pause_btn.setVisible(True)
            elif status == 'Completed':
                self.progress_title.setText("Download Completed!")
                self.progress_bar.setValue(100)
                self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #10b981; }") # success green
                self.progress_pause_btn.setVisible(False)
                self.progress_cancel_btn.setVisible(False)
                self.progress_done_btn.setVisible(True)
                self.progress_speed_label.setText("Speed: 0 B/s")
                self.progress_eta_label.setText("Finished")
            elif status == 'Failed':
                self.progress_title.setText("Download Failed!")
                self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ef4444; }") # danger red
                self.progress_pause_btn.setVisible(False)
                self.progress_cancel_btn.setVisible(False)
                self.progress_done_btn.setVisible(True)
                self.progress_speed_label.setText("Speed: 0 B/s")
                self.progress_eta_label.setText("Error")
            elif status == 'Cancelled':
                self.progress_title.setText("Download Cancelled")
                self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #71717a; }") # muted gray
                self.progress_pause_btn.setVisible(False)
                self.progress_cancel_btn.setVisible(False)
                self.progress_done_btn.setVisible(True)
                self.progress_speed_label.setText("Speed: 0 B/s")
                self.progress_eta_label.setText("Cancelled")

    @Slot()
    def _toggle_pause_active_download(self):
        if not self.active_download_task_id:
            return
        task = download_manager.tasks.get(self.active_download_task_id)
        if not task:
            return
        status = task.get('status')
        if status == 'Downloading':
            download_manager.pause_task(self.active_download_task_id)
        elif status == 'Paused':
            download_manager.resume_task(self.active_download_task_id)

    @Slot()
    def _cancel_active_download(self):
        if self.active_download_task_id:
            download_manager.cancel_task(self.active_download_task_id)

    @Slot()
    def _reset_downloader(self):
        self.active_download_task_id = None
        self.url_input.clear()
        self.result_card.setVisible(False)
        self.progress_frame.setVisible(False)
        self.precheck_frame.setVisible(False)
        self.config_group.setVisible(True)
        self.add_queue_btn.setVisible(True)
        self.download_now_btn.setVisible(True)
        self.playlist_options_frame.setVisible(False)
        self.playlist_range_check.setChecked(False)
        self.playlist_items_input.clear()
        self.noplaylist_check.setVisible(False)
        self.noplaylist_check.setChecked(False)
        self.current_analysis = {}
        self.status_label.setText("Enter a URL above to analyze and download videos.")
        self.status_label.setVisible(True)

    @Slot(int)
    def _on_playlist_range_checked(self, state: int):
        is_checked = state == Qt.Checked.value
        self.playlist_range_widgets.setEnabled(is_checked)

    @Slot(str)
    def _on_url_changed(self, text: str):
        text = text.strip()
        # Check if URL contains both a video and a playlist
        has_video = "v=" in text or "watch?" in text
        has_playlist = "list=" in text
        if has_video and has_playlist:
            self.noplaylist_check.setVisible(True)
            # If "index=" is also present, check it by default to fulfill single-video intent
            if "index=" in text:
                self.noplaylist_check.setChecked(True)
            else:
                self.noplaylist_check.setChecked(False)
        else:
            self.noplaylist_check.setVisible(False)
            self.noplaylist_check.setChecked(False)

    @staticmethod
    def _format_duration(duration_seconds: int) -> str:
        minutes, seconds = divmod(duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    # ── Playlist helpers ─────────────────────────────────────────────

    def _get_playlist_entries(self) -> list:
        """Return the materialised list of playlist entries."""
        entries = self.current_analysis.get('_entries_list') or self.current_analysis.get('entries', [])
        if entries is None:
            return []
        if not isinstance(entries, list):
            try:
                entries = list(entries)
            except Exception:
                entries = []
        return entries

    def _is_playlist(self) -> bool:
        """True if the currently analyzed item is a playlist."""
        if not self.current_analysis:
            return False
        return (
            self.current_analysis.get('_type') == 'playlist'
            or 'entries' in self.current_analysis
        )

    # ── First-video format loading ────────────────────────────────────

    def _load_first_video_formats(self):
        """Kick off PlaylistFirstVideoAnalyzer on the first entry's URL."""
        entries = self._get_playlist_entries()
        if not entries:
            return

        first = entries[0]
        vid_id = first.get('id', '')
        url = (
            first.get('url')
            or first.get('webpage_url')
            or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
        )
        if not url:
            return

        # Show loading state in format combos
        self.video_format_combo.clear()
        self.video_format_combo.addItem("⏳ Loading from first video…")
        self.audio_format_combo.clear()
        self.audio_format_combo.addItem("Please wait…")
        self.video_format_combo.setEnabled(False)
        self.audio_format_combo.setEnabled(False)

        # Cancel previous analyser WITHOUT blocking the UI thread
        if self.first_video_analyzer and self.first_video_analyzer.isRunning():
            self.first_video_analyzer.cancel()
            try:
                self.first_video_analyzer.analysis_completed.disconnect()
                self.first_video_analyzer.analysis_failed.disconnect()
            except RuntimeError:
                pass
            self.terminating_analyzers.add(self.first_video_analyzer)
            self.first_video_analyzer.finished.connect(lambda a=self.first_video_analyzer: self._handle_analyzer_terminated(a))

        self.first_video_analyzer = PlaylistFirstVideoAnalyzer(url)
        self.first_video_analyzer.analysis_completed.connect(self._on_first_video_analyzed)
        self.first_video_analyzer.analysis_failed.connect(self._on_first_video_analysis_failed)
        self.first_video_analyzer.start()

    @Slot(dict)
    def _on_first_video_analyzed(self, info: dict):
        self._parse_formats(info)
        self.video_format_combo.setEnabled(True)
        self.audio_format_combo.setEnabled(True)

    @Slot(str)
    def _on_first_video_analysis_failed(self, error: str):
        self.video_format_combo.clear()
        self.video_format_combo.addItem("⚠ Could not load formats")
        self.audio_format_combo.clear()
        self.audio_format_combo.addItem("⚠ Could not load formats")
        self.video_format_combo.setEnabled(False)
        self.audio_format_combo.setEnabled(False)
        logger.warning(f"First-video analysis failed: {error}")

    # ── Playlist queuing and parsing ─────────────────────────────────

    def _parse_items_spec(self, spec: str, total: int) -> set:
        indices = set()
        parts = spec.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start_str, end_str = part.split('-', 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    indices.update(range(start, end + 1))
                except ValueError:
                    pass
            else:
                try:
                    indices.add(int(part))
                except ValueError:
                    pass
        return {i for i in indices if 1 <= i <= total}

    def _add_playlist_to_queue(self, action: str):
        entries = self._get_playlist_entries()
        if not entries:
            QMessageBox.warning(self, "No Entries", "No playlist entries found.")
            return

        # Determine selected entries based on range controls
        selected_entries = []
        if self.playlist_range_check.isChecked():
            items_spec = self.playlist_items_input.text().strip()
            if items_spec:
                selected_indices = self._parse_items_spec(items_spec, len(entries))
            else:
                start = self.playlist_start_spin.value()
                end = self.playlist_end_spin.value()
                selected_indices = set(range(start, end + 1))
            
            for idx, entry in enumerate(entries):
                playlist_index = entry.get('playlist_index')
                if playlist_index is None:
                    playlist_index = idx + 1
                if playlist_index in selected_indices:
                    selected_entries.append((playlist_index, entry))
        else:
            for idx, entry in enumerate(entries):
                playlist_index = entry.get('playlist_index')
                if playlist_index is None:
                    playlist_index = idx + 1
                selected_entries.append((playlist_index, entry))

        selected_entries.sort(key=lambda x: x[0])

        base_opts = self._build_ydl_opts()
        base_opts.pop('playliststart', None)
        base_opts.pop('playlistend', None)
        base_opts.pop('playlist_items', None)
        base_opts['noplaylist'] = True

        mode_idx = self.mode_combo.currentIndex()

        for playlist_idx, entry in selected_entries:
            vid_id = entry.get('id', '')
            url = (
                entry.get('url')
                or entry.get('webpage_url')
                or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
            )
            if not url:
                continue
            title = entry.get('title') or f"Video {playlist_idx}"
            
            opts = base_opts.copy()
            if mode_idx in (1, 3):
                opts['_check_format_availability'] = True
                opts['_requested_video_format'] = self.video_format_combo.currentData()
                if mode_idx == 3:
                    opts['_requested_audio_format'] = self.audio_format_combo.currentData()
                else:
                    opts['_requested_audio_format'] = ''

            download_manager.add_task(url, title, opts, None)

        if action == 'download':
            self.main_window.switch_tab(1)  # Switch to Queue tab
            self._reset_downloader()
        else:
            self.url_input.clear()
            self.result_card.setVisible(False)
            self.status_label.setText(f"Added {len(selected_entries)} videos to Queue.")
            self.status_label.setVisible(True)

    def _cancel_precheck(self):
        self.precheck_frame.setVisible(False)

    def _start_download_now_task(
        self,
        url: str,
        title: str,
        thumb_path: Optional[str],
        ydl_opts: Dict[str, Any]
    ):
        """Add the task and switch the UI to the progress view."""
        task_id = download_manager.add_task(url, title, ydl_opts, thumb_path)
        self.active_download_task_id = task_id

        self.config_group.setVisible(False)
        self.add_queue_btn.setVisible(False)
        self.download_now_btn.setVisible(False)

        self.progress_frame.setVisible(True)
        self.progress_title.setText("Downloading…")
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("")
        self.progress_speed_label.setText("Speed: 0 B/s")
        self.progress_eta_label.setText("ETA: Queued")
        self.progress_size_label.setText("Size: 0 B / Unknown")
        self.progress_pause_btn.setText("Pause")
        self.progress_pause_btn.setEnabled(True)
        self.progress_pause_btn.setVisible(True)
        self.progress_cancel_btn.setEnabled(True)
        self.progress_cancel_btn.setVisible(True)
        self.progress_done_btn.setVisible(False)
