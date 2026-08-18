import os
import re
import shutil
import subprocess
from pathlib import Path

from .logger import get_logger

logger = get_logger("ffmpeg_check")


def find_ffmpeg(custom_path: str | None = None) -> tuple[str | None, str | None]:
    """
    Find ffmpeg and ffprobe executables.
    1. Checks custom_path (directory or direct executable).
    2. Uses shutil.which for system PATH detection.
    3. Scans common installation locations across Windows/Linux/macOS.
    Returns (ffmpeg_path, ffprobe_path).
    """
    ffmpeg_exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_exe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"

    ffmpeg_found: str | None = None
    ffprobe_found: str | None = None

    if custom_path:
        cp = Path(custom_path)
        if cp.is_dir():
            ff = cp / ffmpeg_exe_name
            fp = cp / ffprobe_exe_name
            if ff.exists() and os.access(ff, os.X_OK):
                ffmpeg_found = str(ff)
            if fp.exists() and os.access(fp, os.X_OK):
                ffprobe_found = str(fp)
        elif cp.is_file() and os.access(cp, os.X_OK):
            ffmpeg_found = str(cp)
            fp = cp.parent / ffprobe_exe_name
            if fp.exists() and os.access(fp, os.X_OK):
                ffprobe_found = str(fp)

    # Primary detection via shutil.which
    if not ffmpeg_found:
        ffmpeg_found = shutil.which(ffmpeg_exe_name) or shutil.which("ffmpeg")
    if not ffprobe_found:
        ffprobe_found = shutil.which(ffprobe_exe_name) or shutil.which("ffprobe")

    # Fallback search locations
    if not ffmpeg_found:
        candidate_paths = []
        if os.name == "nt":
            user_config_ff = Path(os.path.expanduser("~/.config/gui-yt-dlp/ffmpeg"))
            candidate_paths = [
                user_config_ff,
                user_config_ff / "bin",
                Path("C:/ffmpeg/bin"),
                Path("C:/Program Files/ffmpeg/bin"),
                Path("C:/Program Files (x86)/ffmpeg/bin"),
                Path(os.path.expandvars("%LOCALAPPDATA%/Programs/ffmpeg/bin")),
            ]
            # Recursively append any bin subdirectories inside user_config_ff
            if user_config_ff.exists():
                for sub in user_config_ff.glob("**/bin"):
                    if sub.is_dir() and sub not in candidate_paths:
                        candidate_paths.insert(0, sub)
        else:
            candidate_paths = [
                Path(os.path.expanduser("~/.config/gui-yt-dlp/ffmpeg")),
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path("/opt/homebrew/bin"),
                Path("/usr/bin/ffmpeg"),
            ]

        for p in candidate_paths:
            if p.is_dir():
                ff = p / ffmpeg_exe_name
                if ff.exists() and os.access(ff, os.X_OK):
                    ffmpeg_found = str(ff)
                    fp = p / ffprobe_exe_name
                    if fp.exists() and os.access(fp, os.X_OK):
                        ffprobe_found = str(fp)
                    break

    logger.debug(f"Resolved ffmpeg: {ffmpeg_found}, ffprobe: {ffprobe_found}")
    return ffmpeg_found, ffprobe_found


def get_ffmpeg_version(ffmpeg_path: str) -> str | None:
    """Runs ffmpeg -version and extracts the version string."""
    if not ffmpeg_path or not os.path.exists(ffmpeg_path):
        return None

    try:
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            check=True,
        )
        first_line = result.stdout.split("\n")[0]
        match = re.search(r"version\s+([^\s]+)", first_line)
        if match:
            return match.group(1)
        return first_line.strip()
    except Exception as e:
        logger.error(f"Error getting ffmpeg version: {e}")
        return None
