# yt-dlp Flow: Modern Python & PySide6 Desktop Downloader

A premium, modern dark-themed desktop frontend for `yt-dlp` built using Python 3.12+ and PySide6 (Qt6). This app separates GUI rendering from download tasks using worker threads (`QThread`), ensuring that the UI remains highly responsive, even when performing concurrent downloads or post-processing (e.g., audio extraction with FFmpeg).

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/download.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/download.svg?color=%2324292f" width="22" height="22" align="absmiddle" alt="download"></picture> Downloads

Get the pre-compiled standalone application for your platform from the [Releases Page](https://github.com/SudhanshuMatrix/gui-yt-dlp/releases):

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/simple-icons/linux.svg?color=%23e6edf3"><img src="https://api.iconify.design/simple-icons/linux.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="linux"></picture> Linux (Debian / Ubuntu)
* **Installer (.deb)**: [Download latest gui-yt-dlp_amd64.deb](https://github.com/SudhanshuMatrix/gui-yt-dlp/releases/latest)
  * *Includes full system application menu launcher integration and custom branding logo.*
* **Standalone Portable Binary**: [Download latest gui-yt-dlp-linux](https://github.com/SudhanshuMatrix/gui-yt-dlp/releases/latest)
  * *Single portable ELF executable file (no installation required).*

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/simple-icons/windows.svg?color=%23e6edf3"><img src="https://api.iconify.design/simple-icons/windows.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="windows"></picture> Windows (10 / 11)
* **Standalone Portable Executable (.exe)**: [Download latest gui-yt-dlp-windows.exe](https://github.com/SudhanshuMatrix/gui-yt-dlp/releases/latest)
  * *Single portable Windows executable (no installation required).*

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/simple-icons/apple.svg?color=%23e6edf3"><img src="https://api.iconify.design/simple-icons/apple.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="macos"></picture> macOS (Intel / Apple Silicon)
* **Standalone Portable Binary**: [Download latest gui-yt-dlp-macos](https://github.com/SudhanshuMatrix/gui-yt-dlp/releases/latest)
  * *Single portable macOS binary (no installation required).*

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/folder-open.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/folder-open.svg?color=%2324292f" width="22" height="22" align="absmiddle" alt="folder"></picture> Project Structure

```
gui-yt-dlp/
├── pyproject.toml              # Build & dependency declarations (PEP 621)
├── requirements.txt            # Python pip dependencies
├── README.md                   # Installation, build, & usage instructions
├── Makefile                    # Automation commands (run, build, deb, clean, etc.)
├── gui-yt-dlp.spec             # PyInstaller spec build file
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # JSON settings manager (~/.config/gui-yt-dlp/settings.json)
│   ├── download_manager.py     # Asynchronous task scheduling and worker control
│   ├── yt_dlp_worker.py        # QThread workers for URL analysis & downloads
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Core window with Header and tab selectors
│   │   ├── downloader_tab.py   # URL input, meta analysis, formats selector
│   │   ├── queue_tab.py        # Table list of tasks with custom controls & live console log
│   │   ├── settings_tab.py     # Directories paths, theme selection, & live updater
│   │   ├── themes.py           # Custom QSS stylesheets for dark mode themes
│   │   └── assets/
│   │       └── logo.jpeg       # Application logo and window icon
│   └── utils/
│       ├── __init__.py
│       ├── ffmpeg_check.py     # FFmpeg & FFprobe location and version detection
│       └── logger.py           # Application console and file logger
```

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/rocket.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/rocket.svg?color=%2324292f" width="22" height="22" align="absmiddle" alt="rocket"></picture> Installation & Quick Start

### 1. Prerequisites
- Python 3.12 or newer.
- **FFmpeg** and **FFprobe** installed and added to your system's PATH.
  - *Ubuntu/Debian:* `sudo apt install ffmpeg`
  - *Arch Linux:* `sudo pacman -S ffmpeg`
  - *Fedora:* `sudo dnf install ffmpeg`

### 2. Quick Start with Makefile
We provide a `Makefile` for automated setup, execution, and cleaning:
```bash
# 1. Setup virtual environment and install requirements
make venv

# 2. Run the application
make run

# 3. Clean temporary and build files
make clean
```

Or do it manually:
```bash
# Clone or navigate to the repository
cd gui-yt-dlp/

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Start the application
python3 -m src.main
```

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/package.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/package.svg?color=%2324292f" width="22" height="22" align="absmiddle" alt="package"></picture> Packaging & Distribution Instructions

### 1. PyInstaller (Single Binary Executable)
To package the application as a standalone executable folder or single file:
```bash
# Build using the Makefile shortcut
make build  # or 'make exe'
```
The output executable will be generated inside the `dist/gui-yt-dlp` directory, containing the embedded branding logo.

### 2. Debian (.deb) Package
To build a standard Debian install package:
```bash
# Package the standalone binary into a .deb package
make deb
```
This builds and places `gui-yt-dlp_1.0.0_amd64.deb` in the root. Once installed:
- It creates a desktop shortcut in the system application menu labeled `yt-dlp Flow`.
- It installs the custom `logo.jpeg` as the system icon, making the logo show in the system application drawer!

You can install it directly with:
```bash
make install
```
And uninstall it with:
```bash
make uninstall
```

### 3. AppImage (Portable Linux App)
To package as an AppImage, you can use `appimage-builder`:
1. Install `appimage-builder` (refer to [AppImage Builder Docs](https://appimage-builder.readthedocs.io/)).
2. Create an `appimage-builder.yml` file:
   ```yaml
   version: 1
   AppDir:
     path: ./AppDir
     app_info:
       id: org.gui-yt-dlp
       name: gui-yt-dlp
       icon: utilities-terminal
       version: 1.0.1
       exec: usr/bin/python3
       exec_args: "$APPDIR/usr/bin/gui-yt-dlp"
     apt:
       arch: amd64
       sources:
         - feed: deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe
       include:
         - python3
         - python3-pip
         - python3-pyside6
         - ffmpeg
   AppImage:
     update-information: 'none'
     sign-key: 'None'
     arch: x86_64
   ```
3. Run: `appimage-builder --recipe appimage-builder.yml`.

### 4. Flatpak (Sandboxed Linux App)
To package the app as a Flatpak, write a manifest file named `org.flatpak.gui-yt-dlp.json`:
```json
{
  "app-id": "org.flatpak.gui-yt-dlp",
  "runtime": "org.kde.Platform",
  "runtime-version": "6.6",
  "sdk": "org.kde.Sdk",
  "command": "gui-yt-dlp",
  "modules": [
    {
      "name": "python-requirements",
      "buildsystem": "simple",
      "build-commands": [
        "pip3 install --prefix=/app yt-dlp PySide6 requests"
      ]
    },
    {
      "name": "gui-yt-dlp",
      "buildsystem": "simple",
      "build-commands": [
        "pip3 install --no-deps --prefix=/app ."
      ],
      "sources": [
        {
          "type": "dir",
          "path": "."
        }
      ]
    }
  ]
}
```
Build and install local package:
```bash
flatpak-builder --user --install --force-clean build-dir org.flatpak.gui-yt-dlp.json
flatpak run org.flatpak.gui-yt-dlp
```

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/monitor.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/monitor.svg?color=%2324292f" width="22" height="22" align="absmiddle" alt="monitor"></picture> Application Screens

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/layout-dashboard.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/layout-dashboard.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="dashboard"></picture> 1. Downloader Dashboard
![Downloader Dashboard](screenshots/Downloader%20Dashboard.png)
- **URL Parser**: Paste any video or playlist URL. The dashboard automatically fetches video details and shows a high-quality 16:9 thumbnail preview, title, channel name, and duration.
- **Download Settings**: Customize the download mode (e.g., *Best Quality*, *Video Only*, *Audio Only MP3*, or *Custom Formats*).
- **Playlist Controls**: When a playlist is detected, you can specify ranges (e.g., start downloading from item 4) or enter complex indices (e.g. `1,3,5-10`).
- **Post-Processing Options**: Toggle automatic embedding of subtitles, video thumbnails, metadata, and specify target folders.

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/list-todo.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/list-todo.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="queue"></picture> 2. Download Queue
![Download Queue](screenshots/Download%20Queue.png)
- **Live Progress Grid**: Displays active and queued downloads in a tabular list with live status indicators, thumbnail previews, file size metrics, real-time download speeds, and ETAs.
- **Worker Controls**: Pause, resume, cancel, or remove tasks on the fly without blocking the UI thread.
- **Dynamic Format Selector**: If a video lacks the user-requested format, the task transitions to a warning state labeled `Format Unavailable`. Clicking `Select Format` prompts a dialog with alternative streams available for that specific video so you can select and re-queue.
- **Monospace Console Logs**: An integrated collapsible shell terminal displaying color-coded stdout logs from `yt-dlp` subprocesses for debugging.

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/settings.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/settings.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="settings"></picture> 3. Settings Dashboard
![Settings Dashboard](screenshots/Settings%20Dashboard.png)
- **Directory Paths**: Specify default download destination directories and configure path shortcuts.
- **FFmpeg Engine**: Dynamically scans for FFmpeg and FFprobe binary locations on your system, indicating status in green (found) or red (missing).
- **Concurrency & Themes**: Set concurrent download limits (1-10 files at a time) and select from custom application-wide UI themes (like *Midnight Obsidian*).
- **Speed & Network Optimization**: Configure concurrent fragment downloads (parallel download threads per video), custom HTTP chunk sizes, socket connection timeouts, and client player overrides to bypass YouTube's rate limiting and saturate high-speed internet connections.
- **Component Updates**: Check and upgrade the `yt-dlp` dependency directly in the background.

### <picture><source media="(prefers-color-scheme: dark)" srcset="https://api.iconify.design/lucide/library.svg?color=%23e6edf3"><img src="https://api.iconify.design/lucide/library.svg?color=%2324292f" width="18" height="18" align="absmiddle" alt="library"></picture> 4. Library Dashboard
![Library Dashboard](screenshots/Library%20Dashboard.png)
- **Persistent Bookmarks**: Save analyzed videos and playlists to download at a later time. Saved items are serialized persistently inside `~/.config/gui-yt-dlp/library.json`.
- **Quick Save URL**: Paste a video or playlist URL directly to quick-add it to your library. It auto-fetches uploader details, titles, and thumbnails in the background.
- **Config & Quick Download**: Load saved items straight back into the downloader layout to select custom formats, or start downloading immediately using default best-quality profiles.



