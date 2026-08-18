import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str = "gui-yt-dlp", log_level: str = "DEBUG") -> logging.Logger:
    """Configures and returns a rotating logger with separated console and file outputs."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        level = getattr(logging, log_level.upper(), logging.DEBUG)
        logger.setLevel(level)

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Stream / Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler with rotation (max 5MB, keep 3 backups)
        log_dir = Path.home() / ".config" / "gui-yt-dlp"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "app.log"
            fh = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            print(f"Failed to create file logger: {e}", file=sys.stderr)

    return logger
