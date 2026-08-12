import os
import sys
from pathlib import Path
from typing import Any, Dict

APP_NAME = "gui-yt-dlp"
DEFAULT_VERSION = "1.0.3"

try:
    from importlib.metadata import version as pkg_version
    APP_VERSION = pkg_version(APP_NAME)
except Exception:
    APP_VERSION = DEFAULT_VERSION

DEFAULT_SETTINGS: Dict[str, Any] = {
    "download_directory": str(Path.home() / "Downloads"),
    "ffmpeg_path": "",
    "concurrency": 3,
    "theme": "Midnight Obsidian",
    "auto_update": True,
    "embed_subtitles": False,
    "embed_thumbnail": False,
    "add_metadata": False,
    "preferred_audio_format": "mp3",
    "audio_quality": "192",
    "write_auto_subs": False,
    "subtitle_lang": "en",
    "concurrent_fragments": 5,
    "http_chunk_size": "Disabled (Default)",
    "bypass_throttling": True,
    "socket_timeout": 20,
    "minimize_to_tray": True,
    "show_notifications": True,
    "log_level": "INFO",
}


def get_assets_dir() -> Path:
    """Returns absolute path to gui/assets directory across frozen and source modes."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = Path(sys._MEIPASS) / "src" / "gui" / "assets"
        if not base_dir.exists():
            base_dir = Path(sys._MEIPASS) / "assets"
    else:
        base_dir = Path(__file__).parent / "gui" / "assets"
    return base_dir


def get_asset_path(filename: str) -> str:
    """
    Resolves asset path with graceful fallback between .jpeg and .png formats.
    Returns string path to the resolved file or empty string if not found.
    """
    assets_dir = get_assets_dir()
    target = assets_dir / filename
    if target.exists():
        return str(target)

    # Alternate extension fallback
    if filename.endswith(".jpeg"):
        alt = assets_dir / filename.replace(".jpeg", ".png")
        if alt.exists():
            return str(alt)
    elif filename.endswith(".jpg"):
        alt = assets_dir / filename.replace(".jpg", ".png")
        if alt.exists():
            return str(alt)
    elif filename.endswith(".png"):
        alt = assets_dir / filename.replace(".png", ".jpeg")
        if alt.exists():
            return str(alt)
        alt2 = assets_dir / filename.replace(".png", ".jpg")
        if alt2.exists():
            return str(alt2)

    return str(target)
