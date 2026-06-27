# Changelog

All notable changes to this project will be documented in this file.

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
