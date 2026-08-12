import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from .logger import get_logger
from .url_sanitizer import sanitize_url

logger = get_logger("library_manager")


class LibraryManager:
    def __init__(self):
        self.config_dir: Path = Path.home() / ".config" / "gui-yt-dlp"
        self.library_file: Path = self.config_dir / "library.json"
        self.items: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load library items from library.json."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.library_file.exists():
                with open(self.library_file, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
                logger.info(f"Loaded {len(self.items)} items from library.")
            else:
                self.items = []
                self.save()
        except Exception as e:
            logger.error(f"Error loading library: {e}")
            self.items = []

    def save(self) -> None:
        """Save current library items to library.json atomically."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = self.library_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.items, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_file, self.library_file)
            logger.info("Library saved atomically.")
        except Exception as e:
            logger.error(f"Error saving library: {e}")

    def add_item(
        self,
        url: str,
        title: str,
        uploader: str,
        duration: str,
        type_str: str,
        thumbnail_path: Optional[str] = None,
    ) -> bool:
        """Add a new item to the library, avoiding duplicate URLs."""
        clean_url = sanitize_url(url)
        for item in self.items:
            if item.get("url") == clean_url:
                logger.info(f"URL {clean_url} already in library.")
                return False

        saved_thumb_path: Optional[str] = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                lib_thumb_dir = self.config_dir / "library_thumbnails"
                lib_thumb_dir.mkdir(parents=True, exist_ok=True)
                filename = Path(thumbnail_path).name
                dest_path = lib_thumb_dir / filename
                shutil.copy2(thumbnail_path, dest_path)
                saved_thumb_path = str(dest_path)
            except Exception as e:
                logger.error(f"Failed to copy thumbnail: {e}")
                saved_thumb_path = thumbnail_path

        item = {
            "url": clean_url,
            "title": title,
            "uploader": uploader,
            "duration": duration,
            "type": type_str,
            "thumbnail_local_path": saved_thumb_path,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.items.append(item)
        self.save()
        return True

    def remove_item(self, url: str) -> None:
        """Remove an item from the library and clean up its thumbnail."""
        clean_url = sanitize_url(url)
        new_items = []
        for item in self.items:
            if item.get("url") == clean_url:
                thumb = item.get("thumbnail_local_path")
                if thumb and os.path.exists(thumb) and "library_thumbnails" in thumb:
                    try:
                        os.remove(thumb)
                    except Exception as e:
                        logger.warning(f"Could not delete thumbnail {thumb}: {e}")
            else:
                new_items.append(item)
        self.items = new_items
        self.save()


# Global manager instance
library_manager = LibraryManager()
