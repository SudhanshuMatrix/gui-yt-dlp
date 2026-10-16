Fixed Video Download for https://www.youtube.com/watch?v=A95rliroC8Q&t=819s:

Removed the forced player_client list override in 
downloader_tab.py
 and 
library_tab.py
, which was causing GVS PO token warnings and SABR-only streaming missing format errors (Requested format is not available). Metadata extraction now successfully yields all 27 available formats for this video.
Added dynamic FFmpeg resolution and single-stream fallback when FFmpeg is not installed on the system to prevent merging abort crashes.
Combined Video + Audio Progress Bar & Size Display:

Updated DownloadWorker in 
yt_dlp_worker.py
 to track combined stream totals across video and audio download phases.
The size label now displays combined downloaded bytes / combined total size (e.g. 45.2 MB / 125.4 MB) and the progress bar increases monotonically from 0% to 100% without jumping backwards when switching from video to audio streams.
Other Downloader Bug Fixes:

Video Only Mode Format Selection: Updated 
downloader_tab.py
 so single-video "Video Only" downloads respect the format selected by the user in video_format_combo.
URL Sanitization: Updated 
url_sanitizer.py
 to strip quotes and angle brackets around URLs.

---

Progress Bar Reset Bug Fix (follow-up to the combined progress tracking above):

Found that the "monotonically increasing" progress bar claim above didn't hold in practice: whenever one stream of a combined video+audio download finished (video done, audio about to start — or audio done, about to merge), DownloadWorker._progress_hook emitted a bare {"status": "finished", "filename": ...} event with no downloaded/total/speed/eta keys.
DownloadManager._on_progress read those missing keys as defaults (0) and overwrote the task with progress=0.0, downloaded="0 B", total="Unknown", speed="0 B/s", eta="Unknown" — visibly snapping the progress bar and size label back to 0% in both the Downloader tab and the Queue tab (both subscribe to the same task_updated signal) before the download continued.
Fixed in 
download_manager.py
: _on_progress now ignores status == "finished" stream-completion markers entirely, since the worker already tracks combined totals correctly via _completed_streams / _known_combined_total internally.
Removed the unused/dead _max_total_size attribute on DownloadWorker (leftover from an earlier, incomplete attempt at this same safeguard) in 
yt_dlp_worker.py
.
Added a regression test, test_on_progress_ignores_stream_finished_reset, in 
tests/test_download_manager.py
 to lock in this behavior.

---

Full UI Redesign — Modern & Minimal:

Rewrote 
themes.py
 as a proper flat design system instead of a boxy/bordered one: larger corner radii (8-12px), no gradients on the primary button (flat solid accent fill), borderless QGroupBox sections (title-only separation instead of nested boxes-in-boxes), a pill/segmented QTabBar (selected tab = filled accent pill) replacing the old underline tabs, borderless tables with a subtle per-row divider instead of a visible grid, thinner flat scrollbars, and a slimmer flat QProgressBar.
Added new semantic, theme-aware object names so widgets stop hardcoding hex colors that only matched the default "Midnight Obsidian" theme: QLabel#mutedLabel / #captionLabel for secondary text, QLabel#statusLabel / #headerStatusLabel with a state property (muted/success/danger/warning) driven via a new set_label_state() helper, QPushButton#ghostButton / #ghostPrimaryButton / #iconButton for compact flat row-actions, QWidget#subtleFrame for inset panels, and a QTextEdit#consoleEdit style for the log console.
Reworked the header bar in 
main_window.py
 (flat QFrame#appHeader instead of a hand-overridden "fake card", simplified brand row, a status-dot-prefixed state label) and gave the status bar a real theme rule instead of hardcoded RGB values.
Flattened 
downloader_tab.py
's playlist-range panel (was a dashed 1990s-style box) into a subtle inset panel, rounded the thumbnail placeholder, and moved all progress/precheck caption labels off hardcoded hex onto the new object names — this also removes the double-border look where the "Download Options" group box used to nest inside the already-bordered result card.
Converted the small per-row action buttons in 
queue_tab.py
 and 
library_tab.py
 (Pause/Cancel/Remove, Configure/Quick DL/Remove) from boxed mini-buttons to flat ghost/icon buttons, and made both tables borderless/gridless to match.
Converted all dynamic status-color labels in 
settings_tab.py
 (FFmpeg status, update status) to the new statusLabel + set_label_state() pattern instead of setStyleSheet("color: #hex...") calls scattered through the slots; also escaped "&" in group titles ("Directories && Paths" etc.) to stop Qt from rendering them as mnemonic-underlined accelerators.
Fixed a real rendering bug found while verifying the redesign offscreen: QHeaderView::section { background-color: transparent; } does not reliably inherit the window background in Qt — it was rendering as a solid white bar. Fixed by giving QHeaderView and QHeaderView::section an explicit background-color.
Verified via an offscreen (QT_QPA_PLATFORM=offscreen) PySide6 smoke-render across all 4 tabs, the active-download progress state, the playlist options panel, and all 4 built-in themes (Midnight Obsidian, Electric Indigo, Emerald Forest, Cyberpunk Rust) — no crashes, no leftover hardcoded colors fighting the palette. Full pytest suite (18 tests) still green throughout.

---

UI Pass 2 — Real Elevation (Notion-style), the flat redesign felt lifeless:

User feedback after Pass 1: "modern good minimalist UI does not good" — too flat/lifeless, wanted a Notion-like look instead. Qt Style Sheets have no box-shadow property, so genuine card elevation needs a real QGraphicsDropShadowEffect, not just border/radius tricks.
Added apply_elevation(widget) to 
themes.py
 — attaches a soft drop shadow via QGraphicsDropShadowEffect. Applied it only to top-level "floating" cards (downloader's result_card, library's Quick Save bar, queue's log console, the format-selection dialog's card) — nested panels inside an already-elevated card were deliberately kept flat/tinted (subtleFrame) to avoid stacked double-shadows, and per-row list items (the many-rows playlist fallback dialog) stay flat too since per-row shadows would look noisy, not blocky.
Restructured 
settings_tab.py
 from borderless QGroupBox sections into real Notion-style blocks: a plain QLabel section header followed by its own elevated QFrame#cardFrame body, via two new helpers _section_header() and _elevated_card().
Bumped bg_card/bg_hover/bg_selected/border a visible step lighter than bg_main in all 4 theme palettes in 
themes.py
 so elevated surfaces read as distinct layers instead of nearly-flat tone-on-tone.
Turned the header status label into an actual colored pill badge (tinted background + colored text, Notion tag style) instead of plain colored text, and dropped the now-redundant "●" bullet prefix since the pill's background already conveys state.
Fixed a second real bug found while re-verifying: QDialog had no background rule in the stylesheet at all, so every popup dialog (format selection, playlist fallback) rendered with the OS's default white background behind the dark themed card — very jarring. Added QDialog to the QMainWindow background rule.
Also caught and cleaned up two side effects from my own offscreen verification scripts: one run briefly added a fake task to the real ~/.config/gui-yt-dlp/queue.json (removed, plus its temp dir), and another persisted "Cyberpunk Rust" into the real settings.json while cycling themes (restored to the original "Midnight Obsidian"). Verification scripts now redirect HOME/USERPROFILE to a scratch directory so they can never touch real user data again.
Full pytest suite (18 tests) green, ruff clean (same one pre-existing unrelated PYI041 note), verified via offscreen renders of all 4 tabs, both dialogs, and the dialog-background fix.

---

UI Pass 3 — Full migration to PySide6-Fluent-Widgets (qfluentwidgets):

User feedback: "UI is too ugly make it modern just like today's apps and website... change whatever you want structure page feature add delete or anything you want... remove pyqt or any library install anything just make it modern and minimal." Two rounds of hand-rolled QSS (flat redesign, then manual QGraphicsDropShadowEffect-based elevation) had hit a real ceiling — Qt Style Sheets have no real animation system, no native Mica/Acrylic backdrop, no built-in icon set, and genuinely "modern app" chrome (Windows 11 Settings-style) isn't achievable by hand-styling raw QWidgets.
Installed PySide6-Fluent-Widgets (`pip install PySide6-Fluent-Widgets`, pulls in PySideSix-Frameless-Window + darkdetect), added to 
requirements.txt
, 
pyproject.toml
, and 
gui-yt-dlp.spec
's hiddenimports (qfluentwidgets ships no extra resource/data files to bundle — icons are rendered from SVG strings in code, confirmed by walking the installed package for non-.py files).
Rewrote 
main_window.py
 on top of `FluentWindow` instead of `QMainWindow` + `QTabWidget`: native frameless title bar (minimize/maximize/close), a real left sidebar `NavigationInterface` with icons (Downloader/Queue/Library top, Settings pinned to the bottom) replacing the old horizontal pill tabs, Mica backdrop enabled by default on Windows. `switch_tab(index)` now resolves to `self.switchTo(page)`. The old persistent QStatusBar is gone — `FluentWindow` has no status bar — replaced with `InfoBar` toast notifications for one-off messages (theme applied, FFmpeg ready/failed) and a persistent, dismissible top `InfoBar.warning` banner for the offline state instead of a quiet label nobody would notice.
Rewrote all four tabs (
downloader_tab.py
, 
queue_tab.py
, 
library_tab.py
, 
settings_tab.py
) and both custom dialogs (
format_selection_dialog.py
, 
playlist_fallback_dialog.py
) to use Fluent components throughout: `PushButton`/`PrimaryPushButton` with real icons (`FluentIcon.*`) instead of plain text buttons, `LineEdit`/`ComboBox`/`CheckBox`/`SpinBox`/`SwitchButton` instead of the bare Qt widgets, `CardWidget`/`SimpleCardWidget` for real native card elevation (replacing the old hand-attached `QGraphicsDropShadowEffect` helper entirely), `TableWidget` for the Queue/Library tables, `TextEdit` for the log console, `SmoothScrollArea` for inertial scrolling, and `TitleLabel`/`SubtitleLabel`/`BodyLabel`/`CaptionLabel`/`StrongBodyLabel` for a real built-in typography scale instead of object-name-keyed QSS text roles.
`settings_tab.py` had the biggest structural change: the old `QGroupBox`/`QFormLayout` sections are gone, replaced by the library's native `SettingCardGroup` + `SettingCard` pattern (the same one Windows 11's own Settings app uses) — each setting is now an icon-led card row with a title/description and its control on the right, added via a small `_add_trailing()` helper that mirrors how the library's own `SwitchSettingCard`/`ComboBoxSettingCard` append their controls. `QMessageBox.information/warning/critical` (blocking, notify-only) calls across every tab became non-blocking `InfoBar` toasts; `QMessageBox.question` (yes/no) calls became qfluentwidgets' `MessageBox` overlay dialogs.
Replaced the old 4-named-palette theme system (Midnight Obsidian / Electric Indigo / Emerald Forest / Cyberpunk Rust, each a full hand-authored QSS block in 
themes.py
) with qfluentwidgets' native theming: a Dark Mode switch + a row of 6 accent-color swatches under a new "Personalization" settings group, calling the library's own `setTheme()`/`setThemeColor()` — 446 lines of hand-rolled QSS in 
themes.py
 collapsed to ~30 lines (`apply_saved_appearance()` + the `ACCENT_PRESETS` dict), since qfluentwidgets now owns all the actual styling. Added `dark_mode` (bool) and `accent_color` (hex) keys to 
constants.py
's `DEFAULT_SETTINGS`; the old unused `theme` key is left in place for backward compatibility but no longer read.
Found and worked around a real headless-rendering limitation while re-verifying offscreen: `FluentWindow`'s Mica backdrop requires a live DWM compositor, which `QT_QPA_PLATFORM=offscreen` doesn't provide, so screenshots came back solid white even though `isDarkTheme()` correctly reported `True`. Confirmed by toggling `setMicaEffectEnabled(False)` — the dark theme and all card/control styling render correctly once Mica (which depends on live OS compositing, unavailable headless) is out of the way. Mica stays enabled in the shipped app; the verification harness disables it only for its own screenshots.
`ComboBox.addItem(text, icon=None, userData=None)` in qfluentwidgets has a different signature than `QComboBox.addItem(text, userData)` — the second positional argument is an icon, not user data. Every `addItem(desc, id)` call across the codebase (format dropdowns in all three files that populate them) was updated to the explicit `addItem(desc, userData=id)` form to avoid silently passing format IDs as icons.
Verified behavior, not just that it imports: `test_downloader_tab_options_building` (which exercises `_build_ydl_opts()` through `mode_combo.setCurrentIndex()`, `embed_thumb_check.setChecked()`, etc. — real business logic, not cosmetic) and `test_main_window_instantiation` both still pass unmodified against the new Fluent widgets, confirming the signal/slot API surface (`currentIndexChanged`, `stateChanged`→`checkedChanged` where applicable, `setChecked`, `currentData`) stayed compatible. Full pytest suite (18 tests) green, ruff clean.
`download_manager.py` and 
yt_dlp_worker.py
 (the actual download/progress pipeline, including the progress-reset bug fix from earlier this session) were not touched — this was purely a presentation-layer migration.

---

Feature Pass — closed gaps, added batch add / search / open-folder / theme & notification controls:

User asked to add whatever features would make the app genuinely better. Audited the app for dead config and missing conveniences rather than guessing blind.
Found two config keys that were read by the app but had no UI to control them at all — `show_notifications` and `minimize_to_tray` in 
constants.py
 were used in 
main_window.py
 but 
settings_tab.py
 never exposed a toggle for either, so a user could never change them without hand-editing settings.json. Added both as SwitchButton rows under System & Updates.
Replaced the binary Dark Mode switch in Settings → Personalization with a proper 3-way "App Theme" dropdown (Dark / Light / Follow System), using qfluentwidgets' `Theme.AUTO` (backed by the `darkdetect` dependency already pulled in by PySide6-Fluent-Widgets) to follow the OS setting live — something the library already supported but the UI never surfaced. Added a `theme_mode` string setting to 
constants.py
, with `get_saved_theme_mode()` in 
themes.py
 transparently migrating anyone still on the old boolean `dark_mode` setting.
Added a search/filter box to both the Queue tab (filters by title or status, live as you type, keeps filtering correctly as new tasks are added) and the Library tab (filters by title or channel, shows "N / total" in the count label while filtering).
Added an "Open Folder" action to every row in the Queue tab, next to Pause/Cancel/Remove — a common download-manager convenience that was completely missing (there was no way to jump to a finished download without leaving the app). Implemented via a new small cross-platform 
src/utils/open_path.py
 helper (`os.startfile` / `open` / `xdg-open`) rather than inlining platform-specific code into the GUI layer, since downloads already track their destination folder per-task.
Added a "Batch Add" button to the Downloader tab, opening a new 
src/gui/widgets/batch_add_dialog.py
 (a `MessageBoxBase` overlay, consistent with the other dialogs) where you paste many URLs — one per line — and queue them all at once. Deliberately scoped to only "Best Quality" / "Audio Only (MP3)" as quality choices, since those are the two modes that don't need a specific per-video format ID the way "Video Only"/"Custom Formats" do (a format ID picked for one video usually doesn't exist on another) — those two modes remain a single-URL, analyze-first flow. Reuses the container/thumbnail/metadata preferences already set in the main Download Options panel.
Verified every addition individually (instantiate + exercise the new method/dialog directly) before wiring it in, then re-ran the full offscreen screenshot pass across all 4 tabs plus the new Batch Add dialog standalone (confirming it renders correctly as a proper modal overlay with its fade-in animation, once I accounted for that animation needing a frame to advance before grabbing a verification screenshot — not a bug, just a test-harness timing detail). Full pytest suite (18 tests) green, ruff clean (same pre-existing unrelated PYI041 note).
