from pathlib import Path

from src.utils.library_manager import LibraryManager


def test_library_manager_add_and_remove(tmp_path: Path):
    lib = LibraryManager()
    lib.config_dir = tmp_path
    lib.library_file = tmp_path / "library.json"
    lib.items = []

    # Add item
    added = lib.add_item(
        url="https://www.youtube.com/watch?v=test12345",
        title="Test Title",
        uploader="Test Channel",
        duration="03:45",
        type_str="Video",
    )
    assert added is True
    assert len(lib.items) == 1

    # Duplicate add
    dup = lib.add_item(
        url="https://www.youtube.com/watch?v=test12345",
        title="Test Title",
        uploader="Test Channel",
        duration="03:45",
        type_str="Video",
    )
    assert dup is False
    assert len(lib.items) == 1

    # Remove item
    lib.remove_item("https://www.youtube.com/watch?v=test12345")
    assert len(lib.items) == 0
