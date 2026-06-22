import shutil
import subprocess
import os
import re
from typing import Optional, Tuple
from .logger import get_logger

logger = get_logger("ffmpeg_check")

def find_ffmpeg(custom_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Find ffmpeg and ffprobe. If custom_path is specified, checks there first.
    Returns (ffmpeg_path, ffprobe_path).
    """
    ffmpeg_exe = "ffmpeg"
    ffprobe_exe = "ffprobe"

    if custom_path:
        # Check if custom path is a directory containing the executables
        if os.path.isdir(custom_path):
            ff_path = os.path.join(custom_path, ffmpeg_exe)
            fp_path = os.path.join(custom_path, ffprobe_exe)
            if os.path.exists(ff_path) and os.access(ff_path, os.X_OK):
                ffmpeg_exe = ff_path
            if os.path.exists(fp_path) and os.access(fp_path, os.X_OK):
                ffprobe_exe = fp_path
        # Check if custom path is the direct path to ffmpeg executable
        elif os.path.exists(custom_path) and os.access(custom_path, os.X_OK):
            ffmpeg_exe = custom_path
            # Try to guess ffprobe path from ffmpeg dir
            custom_dir = os.path.dirname(custom_path)
            fp_path = os.path.join(custom_dir, ffprobe_exe)
            if os.path.exists(fp_path) and os.access(fp_path, os.X_OK):
                ffprobe_exe = fp_path

    # Try resolving paths
    ffmpeg_path = shutil.which(ffmpeg_exe)
    ffprobe_path = shutil.which(ffprobe_exe)

    logger.debug(f"Resolved ffmpeg: {ffmpeg_path}, ffprobe: {ffprobe_path}")
    return ffmpeg_path, ffprobe_path

def get_ffmpeg_version(ffmpeg_path: str) -> Optional[str]:
    """
    Runs ffmpeg -version and extracts the version string.
    """
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            check=True
        )
        first_line = result.stdout.split('\n')[0]
        # Match 'ffmpeg version N-...' or 'ffmpeg version 4.4...'
        match = re.search(r"version\s+([^\s]+)", first_line)
        if match:
            return match.group(1)
        return first_line
    except Exception as e:
        logger.error(f"Error getting ffmpeg version: {e}")
        return None
