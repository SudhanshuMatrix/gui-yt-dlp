import re
from urllib.parse import urlparse


def is_valid_url(url: str | None) -> bool:
    """Check if the provided string is a valid HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False

    cleaned = sanitize_url(url)
    try:
        parsed = urlparse(cleaned)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def sanitize_url(url: str | None) -> str:
    """Sanitize URL string by removing leading/trailing whitespace and control characters."""
    if not url or not isinstance(url, str):
        return ""

    cleaned = url.strip()
    # Strip dangerous shell control characters / newlines
    cleaned = re.sub(r"[\r\n\t]", "", cleaned)
    return cleaned
