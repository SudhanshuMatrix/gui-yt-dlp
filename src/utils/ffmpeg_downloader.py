import io
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .logger import get_logger

logger = get_logger("ffmpeg_downloader")

# yt-dlp's official FFmpeg Windows GPL build (always points to the latest release)
FFMPEG_WIN_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
FFMPEG_LINUX_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-linux64-gpl.tar.xz"
)
FFMPEG_MAC_URL = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"

# Destination inside the app's config dir  (~/.config/gui-yt-dlp/ffmpeg)
APP_FFMPEG_DIR = Path(os.path.expanduser("~/.config/gui-yt-dlp/ffmpeg"))


def get_managed_ffmpeg_bin() -> Path | None:
    """Return the *bin* directory of an already-managed FFmpeg installation, or None."""
    if not APP_FFMPEG_DIR.exists():
        return None
    # Search one level deep for a 'bin' folder containing ffmpeg(.exe)
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for bin_dir in APP_FFMPEG_DIR.glob("**/bin"):
        if bin_dir.is_dir() and (bin_dir / exe_name).exists():
            return bin_dir
    return None


class FfmpegDownloadWorker(QThread):
    """
    Downloads and extracts FFmpeg binaries into the app's config directory.
    Emits progress_updated(int percent, str message) and finished signals.
    """

    progress_updated = Signal(int, str)  # percent (0-100), status message
    download_finished = Signal(bool, str)  # success, message / error

    def run(self):
        try:
            import requests
        except ImportError:
            self.download_finished.emit(False, "The 'requests' library is not installed.")
            return

        if os.name == "nt":
            url = FFMPEG_WIN_URL
        elif os.name == "posix" and "darwin" in __import__("platform").system().lower():
            url = FFMPEG_MAC_URL
        else:
            url = FFMPEG_LINUX_URL

        logger.info(f"Downloading FFmpeg from: {url}")
        self.progress_updated.emit(0, "Starting FFmpeg download…")

        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunks = []

            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 85)
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        self.progress_updated.emit(
                            percent, f"Downloading… {mb:.1f} / {total_mb:.1f} MB"
                        )

            self.progress_updated.emit(87, "Extracting archive…")
            data = b"".join(chunks)

            # Clean out old managed install
            if APP_FFMPEG_DIR.exists():
                shutil.rmtree(APP_FFMPEG_DIR, ignore_errors=True)
            APP_FFMPEG_DIR.mkdir(parents=True, exist_ok=True)

            if url.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    zf.extractall(APP_FFMPEG_DIR)
            elif url.endswith((".tar.xz", ".tar.gz")):
                with tempfile.NamedTemporaryFile(suffix=".tar.xz", delete=False) as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name
                with tarfile.open(tmp_path) as tf:
                    tf.extractall(APP_FFMPEG_DIR)
                os.unlink(tmp_path)

            self.progress_updated.emit(98, "Verifying installation…")

            bin_dir = get_managed_ffmpeg_bin()
            if not bin_dir:
                self.download_finished.emit(
                    False,
                    "Extraction succeeded but ffmpeg executable was not found. "
                    "Please set the FFmpeg path manually in Settings.",
                )
                return

            self.progress_updated.emit(100, "FFmpeg installed successfully!")
            self.download_finished.emit(True, f"FFmpeg downloaded and installed to:\n{bin_dir}")
            logger.info(f"FFmpeg installed at: {bin_dir}")

        except Exception as e:
            logger.error(f"FFmpeg download failed: {e}")
            self.download_finished.emit(False, f"Download failed: {e}")
