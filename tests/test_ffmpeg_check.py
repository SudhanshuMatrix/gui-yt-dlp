from src.utils.ffmpeg_check import find_ffmpeg, get_ffmpeg_version


def test_find_ffmpeg_returns_tuple():
    ff, fp = find_ffmpeg()
    # Returns (path_or_none, path_or_none)
    assert ff is None or isinstance(ff, str)
    assert fp is None or isinstance(fp, str)


def test_get_ffmpeg_version_nonexistent():
    version = get_ffmpeg_version("/nonexistent/path/to/ffmpeg")
    assert version is None
