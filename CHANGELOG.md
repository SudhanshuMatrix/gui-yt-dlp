# Changelog

All notable changes to this project will be documented in this file.

---

## [1.0.3] - 2026-08-12

### Added
- **FFmpeg Auto-Downloader**:
  - On startup, if FFmpeg is not found the app silently downloads and installs managed FFmpeg binaries in the background via the new `FfmpegDownloadWorker`.
  - Progress is displayed in the status bar and header. On success the path is automatically saved to config so future launches skip the download.
  - Added retry support from Settings → Auto-Download FFmpeg if the silent download fails.
- **Drag-and-Drop URL Input**:
  - The Downloader tab now accepts URLs dragged directly from a browser address bar or any text source and immediately begins analysis.
- **System Tray Integration**:
  - App can be minimized to the system tray with a right-click menu: Show, Pause All, Resume All, Quit.
  - Download completion notifications appear as tray balloon messages.
- **Keyboard Shortcuts**:
  - `Ctrl+1..4` to switch tabs, `Ctrl+P` to pause all downloads, `Ctrl+R` to refresh the library.
- **Queue Persistence**:
  - The download queue is now saved to `~/.config/gui-yt-dlp/queue.json` atomically on every status change and restored on next launch (previously active downloads resume as Paused, ready to continue).
- **URL Sanitizer Module** (`src/utils/url_sanitizer.py`):
  - Dedicated `is_valid_url()` and `sanitize_url()` helpers used throughout the app to strip control characters and validate URLs before they reach subprocesses or yt-dlp.
- **Single Version Source of Truth** (`src/constants.py`):
  - `APP_VERSION` is now read from package metadata via `importlib.metadata` at runtime; `pyproject.toml` is the sole version definition. All UI labels, `setApplicationVersion`, and CI scripts derive from this.
- **Rotating Log Files**:
  - File handler upgraded to `RotatingFileHandler` (5 MB max, 3 backups) to prevent unbounded log growth.
- **CI Workflow** (`.github/workflows/ci.yml`):
  - Automated lint (ruff), formatting check (black), type check (mypy), and pytest on every push and pull request.
- **Pre-commit Hooks** (`.pre-commit-config.yaml`):
  - black, ruff, isort, and trailing-whitespace hooks wired up for contributor workflow.
- **Unit Test Suite** (`tests/`):
  - 12 tests covering constants, config debouncing and atomic writes, URL sanitizer, FFmpeg detection, library manager, download manager lifecycle, and MainWindow instantiation.
- **AI Disclosure Policy**:
  - `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and the new GitHub PR template (`.github/pull_request_template.md`) require contributors to disclose AI assistance with model name and confirm manual review before submission.
- **Community Files**: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/dependabot.yml`.
- **`pyproject.toml` improvements**: Added `license`, `keywords`, `classifiers`, `maintainers`, `[project.urls]`, and `[project.optional-dependencies] dev` extras.

### Fixed
- **Logo file mismatch**: `main.py` and `main_window.py` now resolve assets via `get_asset_path()` which falls back between `.jpeg` and `.png` automatically — no more broken app icon.
- **Inconsistent version strings**: Removed hard-coded `"1.0.0"` and `"v1.0.1"` strings; all version references now pull from `constants.APP_VERSION`.
- **Unsafe yt-dlp updater**: `YtdlUpdateWorker` no longer guesses pip binary paths. It now invokes `[sys.executable, "-m", "pip", ...]` to stay within the active venv and reports the installed version via `yt_dlp.__version__` (not `__name__`).
- **Non-atomic config writes**: `AppConfig.save()` now writes to a `.tmp` file and uses `os.replace()` for crash-safe atomicity. `AppConfig.set()` schedules a debounced save via `threading.Timer` instead of writing on every keystroke.
- **FFmpeg discovery**: `find_ffmpeg()` now uses `shutil.which` as the primary resolver and falls back to scanning common OS installation directories (`C:/ffmpeg/bin`, `/usr/local/bin`, `/opt/homebrew/bin`, etc.). Custom path accepts both a directory and a direct executable.
- **`changeEvent` AttributeError**: Fixed `QEvent.Type.WindowStateChange` enum reference that caused an `AttributeError` on PySide6 6.x under test.
- **Worker thread cleanup**: `terminating_workers` changed from `set` to `list` (hashable-safe for QThread objects). Signals are reliably disconnected before cancelling workers on pause/cancel.
- **Library manager atomic saves**: `library.json` is now written atomically, consistent with config saves.

### Changed
- FFmpeg browse button in Settings now opens a file picker first (for selecting an executable directly) then a directory picker as fallback — replacing the directory-only dialog.
- `Makefile` now reads `VERSION` dynamically from `pyproject.toml` via `tomllib` and adds `test`, `lint`, `format`, `check` targets.

---

## [1.0.2] - 2026-07-01

### Added
- **Speed & Network Optimization Settings**:
  - Added concurrent fragment download configuration to allow parallel downloading of up to 16 stream fragments (saturating high-speed connections to match speed test capacities).
  - Integrated automated player client signature overrides (`-android_sdkless`) to bypass YouTube's modern adaptive download speed throttling.
  - Added custom HTTP chunk sizing controls and connection socket timeout configuration.
  - Exposed all network controls in a new **Speed & Network Optimization** settings group.
- **Responsive Settings Dashboard Layout**:
  - Refactored Settings Tab to utilize a scrollable container (`QScrollArea`), preventing layout compression or widget collapse under custom window sizing.
  - Implemented `QFormLayout` for Settings sections to provide aligned label-to-control columns.
  - Explicitly styled group boxes with card backgrounds (`bg_card`) matching the selected theme.

### Fixed
- Resolved layout overlap and transparency issues in the settings dashboard caused by cascading stylesheet inheritance on the scroll content container.

---

## [1.0.1] - 2026-06-27

### Added
- **Library Tab (Saved for Later)**:
  - Add bookmarks dynamically using a "Save to Library" button in the Downloader tab.
  - Paste any URL into a "Quick Save URL" box in the Library to save items directly.
  - View saved details: Thumbnails (pre-cached locally), Title, Channel Name, and Duration.
  - Direct actions: **Configure** (loads URL back to the downloader) or **Quick DL** (queues download with default high-quality profiles).
- **Auto-Pause/Resume on Network Outage**:
  - Continuous network status polling via an asynchronous socket monitor thread.
  - Automatically pauses downloading tasks when internet is lost and resumes them when connection is restored.
  - Intercepts connection timeout errors to transition tasks to a "Paused" state gracefully rather than failing them.
- **Network Speed Test**:
  - Perform live download speed checks from geo-distributed Cloudflare CDN servers directly from the Downloader tab.
- **GitHub Release CI/CD Updates**:
  - macOS platform support added to build binaries automatically.
  - Dynamic release notes extracted from annotated tags, local changelogs, or git history.

### Fixed
- Combined playlist/video links (`v=` and `list=`) no longer force playlist analysis when "Ignore playlist context" is checked.
- Resolved race conditions with Qt layout rendering using robust URL string pattern matching rather than widget visibility indicators.

---

## [1.0.0] - 2026-06-21

### Added
- **Modern Dark-Themed GUI**: Build with PySide6 featuring fluid transitions and glassmorphism elements.
- **Multimodal Video Parser**: Full metadata analyzer displaying thumbnail, author, duration, and available stream qualities.
- **Asynchronous Task Queue**: Tabular list with live progress bars, download speed metrics, and ETAs.
- **FFmpeg Integration**: Automatic path configuration and dependency checker.
- **Update Engine**: Check and update local `yt-dlp` binaries silently in the background.
