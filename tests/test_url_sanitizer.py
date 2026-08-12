from src.utils.url_sanitizer import is_valid_url, sanitize_url


def test_sanitize_url():
    assert sanitize_url("  https://www.youtube.com/watch?v=123  \n\r") == "https://www.youtube.com/watch?v=123"
    assert sanitize_url(None) == ""
    assert sanitize_url("http://example.com/test\tfile") == "http://example.com/testfile"


def test_is_valid_url():
    assert is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_url("http://github.com/yt-dlp/yt-dlp") is True
    assert is_valid_url("ftp://invalid.scheme.com") is False
    assert is_valid_url("not_a_url") is False
    assert is_valid_url("") is False
    assert is_valid_url(None) is False
