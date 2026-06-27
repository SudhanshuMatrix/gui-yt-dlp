import os
import time
import yt_dlp
from typing import Any, Dict, Optional
from PySide6.QtCore import QThread, Signal, QObject
from .utils.logger import get_logger

logger = get_logger("yt_dlp_worker")

class YtdlLogger:
    def __init__(self, worker: QObject):
        self.worker = worker

    def debug(self, msg: str):
        # yt-dlp debug statements can be spammy, but we send them to the log viewer
        if msg.startswith('[download]') and '%' in msg:
            # Avoid sending standard progress updates to log to prevent spamming
            return
        self.worker.log_received.emit(msg.strip())

    def info(self, msg: str):
        self.worker.log_received.emit(msg.strip())

    def warning(self, msg: str):
        self.worker.log_received.emit(f"Warning: {msg.strip()}")

    def error(self, msg: str):
        self.worker.log_received.emit(f"Error: {msg.strip()}")


class VideoAnalyzer(QThread):
    analysis_completed = Signal(dict)
    analysis_failed = Signal(str)

    def __init__(self, url: str, noplaylist: bool = False):
        super().__init__()
        self.url = url
        self.noplaylist = noplaylist
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            logger.info(f"Analyzing URL: {self.url} (noplaylist={self.noplaylist})")
            # Quick configuration for extraction
            ydl_opts = {
                'skip_download': True,
                'no_warnings': True,
                'quiet': True,
                'noplaylist': self.noplaylist,
            }
            if not self.noplaylist:
                ydl_opts['extract_flat'] = 'in_playlist'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.cancelled:
                    return
                # Extract metadata
                info = ydl.extract_info(self.url, download=False)
                
            if self.cancelled:
                return

            if not info:
                self.analysis_failed.emit("Failed to retrieve media metadata.")
                return

            # Download thumbnail in background if available
            thumbnail_url = info.get('thumbnail')
            if thumbnail_url:
                try:
                    thumb_dir = os.path.expanduser("~/.config/gui-yt-dlp/thumbnails")
                    os.makedirs(thumb_dir, exist_ok=True)
                    video_id = info.get('id', 'temp_thumb')
                    thumb_path = os.path.join(thumb_dir, f"{video_id}.jpg")
                    
                    import requests
                    r = requests.get(thumbnail_url, timeout=10)
                    if r.status_code == 200:
                        with open(thumb_path, 'wb') as f:
                            f.write(r.content)
                        info['thumbnail_local_path'] = thumb_path
                        logger.info(f"Downloaded thumbnail to {thumb_path}")
                except Exception as thumb_err:
                    logger.error(f"Failed to download thumbnail: {thumb_err}")

            self.analysis_completed.emit(info)
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            if not self.cancelled:
                self.analysis_failed.emit(str(e))



class FormatUnavailableException(Exception):
    def __init__(self, message: str, info: dict):
        super().__init__(message)
        self.info = info


class DownloadWorker(QThread):
    progress_updated = Signal(dict)
    log_received = Signal(str)
    download_finished = Signal(str)
    error = Signal(str)
    format_unavailable = Signal(dict)

    def __init__(self, url: str, ydl_opts: Dict[str, Any]):
        super().__init__()
        self.url = url
        self.ydl_opts = ydl_opts.copy()
        self._paused = False
        self._cancelled = False
        self.current_filename = ""
        
        # Inject our progress hooks and custom logger
        self.ydl_opts['progress_hooks'] = [self._progress_hook]
        self.ydl_opts['logger'] = YtdlLogger(self)

    def pause(self):
        if not self._paused:
            self._paused = True
            self.log_received.emit("[App] Download paused.")

    def resume(self):
        if self._paused:
            self._paused = False
            self.log_received.emit("[App] Download resumed.")

    def cancel(self):
        self._cancelled = True
        self._paused = False  # Break the pause loop if it's blocked
        self.log_received.emit("[App] Download cancellation requested...")

    def run(self):
        try:
            self.log_received.emit(f"[App] Starting download for: {self.url}")
            
            # Check format availability if requested
            if self.ydl_opts.get('_check_format_availability'):
                video_fmt = self.ydl_opts.get('_requested_video_format')
                audio_fmt = self.ydl_opts.get('_requested_audio_format')
                
                self.log_received.emit("[App] Checking format availability...")
                
                check_opts = {
                    'skip_download': True,
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                }
                
                with yt_dlp.YoutubeDL(check_opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                    
                if self._cancelled:
                    self.error.emit("Download cancelled.")
                    return
                    
                if not info:
                    raise Exception("Failed to retrieve format metadata.")
                    
                formats = info.get('formats', [])
                fmt_ids = {f.get('format_id', '') for f in formats}
                
                video_ok = video_fmt in fmt_ids
                audio_ok = (not audio_fmt) or (audio_fmt in fmt_ids)
                
                if not (video_ok and audio_ok):
                    self.log_received.emit(f"[App] Format not available: video={video_fmt}, audio={audio_fmt}")
                    raise FormatUnavailableException("Requested format is not available.", info)
                    
                self.log_received.emit("[App] Selected format is available. Proceeding with download...")

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.url])

            if self._cancelled:
                self.error.emit("Download cancelled.")
            else:
                self.download_finished.emit(self.current_filename or "Download completed successfully.")
        except FormatUnavailableException as e:
            self.format_unavailable.emit(e.info)
        except Exception as e:
            if self._cancelled:
                self.log_received.emit("[App] Download successfully cancelled.")
                self.error.emit("Download cancelled.")
            else:
                logger.error(f"Download worker error: {e}")
                self.error.emit(str(e))

    def _progress_hook(self, d: Dict[str, Any]):
        # Handle cancellation
        if self._cancelled:
            raise Exception("Download cancelled by user.")

        # Handle pausing
        while self._paused:
            time.sleep(0.1)
            if self._cancelled:
                raise Exception("Download cancelled by user.")

        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            filename = d.get('filename', '')
            self.current_filename = filename

            self.progress_updated.emit({
                'status': 'downloading',
                'downloaded': downloaded,
                'total': total,
                'speed': speed,
                'eta': eta,
                'filename': os.path.basename(filename)
            })
        elif status == 'finished':
            filename = d.get('filename', '')
            self.current_filename = filename
            self.progress_updated.emit({
                'status': 'finished',
                'filename': os.path.basename(filename)
            })


class PlaylistFirstVideoAnalyzer(QThread):
    """Fetches full format metadata for a single video (first entry of a playlist)."""
    analysis_completed = Signal(dict)
    analysis_failed = Signal(str)

    def __init__(self, video_url: str):
        super().__init__()
        self.video_url = video_url
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            logger.info(f"Fetching formats for first playlist video: {self.video_url}")
            ydl_opts = {
                'skip_download': True,
                'no_warnings': True,
                'quiet': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.cancelled:
                    return
                info = ydl.extract_info(self.video_url, download=False)

            if self.cancelled:
                return
            if not info:
                self.analysis_failed.emit("Failed to retrieve format data from first video.")
                return
            self.analysis_completed.emit(info)
        except Exception as e:
            logger.error(f"PlaylistFirstVideoAnalyzer error: {e}")
            if not self.cancelled:
                self.analysis_failed.emit(str(e))


def _build_format_lists(formats: list):
    """Helper: split a formats list into (video_formats, audio_formats) dicts."""
    video_formats = []
    audio_formats = []
    for f in formats:
        fid = f.get('format_id', '')
        if not fid:
            continue
        ext = f.get('ext', '')
        vcodec = str(f.get('vcodec') or 'none').lower()
        acodec = str(f.get('acodec') or 'none').lower()

        if vcodec != 'none':
            height = f.get('height', 0) or 0
            fps = f.get('fps')
            fps_str = f" {fps}fps" if fps and fps > 30 else ""
            is_combined = acodec != 'none'
            if is_combined:
                desc = f"{height}p{fps_str} ({ext}) [Combined]"
            else:
                desc = f"{height}p{fps_str} ({ext})"
            video_formats.append({'id': fid, 'ext': ext, 'height': height, 'is_combined': is_combined, 'desc': desc})
        elif acodec != 'none':
            abr = f.get('abr') or f.get('tbr') or 0
            desc = f"{int(abr)}kbps ({ext})" if abr > 0 else f"Audio ({ext})"
            audio_formats.append({'id': fid, 'ext': ext, 'abr': abr or 0, 'desc': desc})

    video_formats.sort(key=lambda x: x['height'], reverse=True)
    audio_formats.sort(key=lambda x: x['abr'], reverse=True)
    return video_formats, audio_formats


class PlaylistFormatPreCheckWorker(QThread):
    """
    Pre-checks format availability for a playlist using a SINGLE yt-dlp extraction call
    (much faster than N individual calls). Emits an indeterminate progress signal while
    yt-dlp is fetching, then per-entry signals as results are classified.
    """
    progress_updated = Signal(int, int, str)   # current (0=indeterminate), total, label
    check_completed = Signal(list, list)        # compatible_entries, incompatible_entries
    check_failed = Signal(str)

    def __init__(
        self,
        playlist_url: str,
        flat_entries: list,
        video_format_id: str,
        audio_format_id: str,
        playlist_items_spec: str = '',
    ):
        super().__init__()
        self.playlist_url = playlist_url
        self.flat_entries = flat_entries   # lightweight metadata from the initial flat extraction
        self.video_format_id = video_format_id
        self.audio_format_id = audio_format_id  # '' means audio not separately required
        self.playlist_items_spec = playlist_items_spec
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        compatible = []
        incompatible = []

        try:
            ydl_opts: dict = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            }
            if self.playlist_items_spec:
                ydl_opts['playlist_items'] = self.playlist_items_spec

            # Signal indeterminate start (current=0 is the sentinel)
            total_hint = len(self.flat_entries)
            self.progress_updated.emit(0, total_hint, "Fetching format data from playlist…")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.cancelled:
                    return
                info = ydl.extract_info(self.playlist_url, download=False)

            if self.cancelled:
                return

            if not info:
                self.check_failed.emit("Failed to extract playlist information.")
                return

            # Collect full entries (generators already consumed by yt-dlp into a list)
            full_entries = info.get('entries') or []
            if not isinstance(full_entries, list):
                try:
                    full_entries = list(full_entries)
                except Exception:
                    full_entries = []

            total = len(full_entries)

            for idx, entry in enumerate(full_entries):
                if self.cancelled:
                    return

                if not entry:
                    continue

                title = entry.get('title') or f"Video {idx + 1}"
                self.progress_updated.emit(idx + 1, total, title)

                fmt_ids = {f.get('format_id', '') for f in entry.get('formats', [])}
                video_ok = self.video_format_id in fmt_ids
                audio_ok = (not self.audio_format_id) or (self.audio_format_id in fmt_ids)

                avail_video, avail_audio = _build_format_lists(entry.get('formats', []))

                # Use matching flat entry for any extra metadata (thumbnail, etc.)
                flat_entry = self.flat_entries[idx] if idx < len(self.flat_entries) else {}
                vid_id = entry.get('id') or flat_entry.get('id', '')
                url = (
                    entry.get('webpage_url')
                    or flat_entry.get('url')
                    or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else '')
                )

                entry_data = {
                    'id': vid_id,
                    'title': title,
                    'resolved_url': url,
                    'available_video_formats': avail_video,
                    'available_audio_formats': avail_audio,
                    'playlist_index': idx + 1,
                }

                if video_ok and audio_ok:
                    compatible.append(entry_data)
                else:
                    incompatible.append(entry_data)

            if not self.cancelled:
                self.check_completed.emit(compatible, incompatible)

        except Exception as e:
            logger.error(f"PlaylistFormatPreCheckWorker error: {e}")
            if not self.cancelled:
                self.check_failed.emit(str(e))
