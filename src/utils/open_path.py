import os
import subprocess
import sys

from .logger import get_logger

logger = get_logger("open_path")


def open_path(path: str) -> bool:
    """Open a file or folder in the OS's native file browser/handler.

    Returns True if a path existed and an open attempt was made, False if
    the path doesn't exist on disk.
    """
    if not path or not os.path.exists(path):
        return False

    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as e:
        logger.error(f"Failed to open path {path}: {e}")
        return False
