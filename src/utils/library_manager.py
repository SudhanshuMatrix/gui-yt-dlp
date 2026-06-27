import os
import json
import time
from typing import List, Dict, Any
from .logger import get_logger

logger = get_logger("library_manager")

class LibraryManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gui-yt-dlp")
        self.library_file = os.path.join(self.config_dir, "library.json")
        self.items: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load library items from library.json."""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.library_file):
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
        """Save current library items to library.json."""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True)
            with open(self.library_file, "w", encoding="utf-8") as f:
                json.dump(self.items, f, indent=4)
            logger.info("Library saved.")
        except Exception as e:
            logger.error(f"Error saving library: {e}")

    def add_item(self, url: str, title: str, uploader: str, duration: str, type_str: str, thumbnail_path: str = None) -> bool:
        """Add a new item to the library, avoiding duplicate URLs."""
        for item in self.items:
            if item.get("url") == url:
                logger.info(f"URL {url} already in library.")
                return False
        
        # Copy thumbnail to a permanent place in the library
        saved_thumb_path = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                lib_thumb_dir = os.path.join(self.config_dir, "library_thumbnails")
                os.makedirs(lib_thumb_dir, exist_ok=True)
                filename = os.path.basename(thumbnail_path)
                dest_path = os.path.join(lib_thumb_dir, filename)
                import shutil
                shutil.copy2(thumbnail_path, dest_path)
                saved_thumb_path = dest_path
            except Exception as e:
                logger.error(f"Failed to copy thumbnail: {e}")
                saved_thumb_path = thumbnail_path

        item = {
            "url": url,
            "title": title,
            "uploader": uploader,
            "duration": duration,
            "type": type_str,
            "thumbnail_local_path": saved_thumb_path,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.items.append(item)
        self.save()
        return True

    def remove_item(self, url: str) -> None:
        """Remove an item from the library and clean up its thumbnail."""
        new_items = []
        for item in self.items:
            if item.get("url") == url:
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
