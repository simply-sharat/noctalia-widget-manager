# Noctalia Widget Manager

A small PySide6 (Qt6) desktop app to view and reorder the bar widgets in
[Noctalia](https://noctalia.dev)'s `settings.json`.

Noctalia's plugin manager always appends new plugin widgets to the **end** of
the bar's right section, so they land at the far right (after the tray and
control center). This tool lets you fix the arrangement: reorder widgets, move
them between the left/center/right sections, and save the result back to the
config file.

## Features

- Three columns matching the bar sections: **Left**, **Center**, **Right**
- Reorder within a section with the ▲ / ▼ buttons or drag-and-drop
- Move widgets between sections with the ◀ / ▶ buttons or drag-and-drop
- **Reload from Disk** — discard unsaved changes and re-read the config
- **Save** — writes back to `settings.json`, preserving every widget's settings
  (e.g. the Tray's pinned items) and taking a `settings.json.bak` backup first

## Requirements

- Python 3.10+
- PySide6 (`pip install PySide6`, or `sudo pacman -S python-pyside6` on Arch)

Only needed to run `main.py` directly. The packaged binary (see below) is
self-contained and needs neither Python nor PySide6.

## Install as a standalone app

Build a single self-contained binary and add it to your system launcher:

```bash
./build.sh     # creates .venv, installs PyInstaller, builds dist/noctalia-widget-manager
./install.sh   # installs the binary + .desktop entry + icon under ~/.local
```

`install.sh` copies the binary to `~/.local/bin/` and registers a
**Noctalia Widget Manager** entry in `~/.local/share/applications/`, so the app
appears in your application launcher and can be pinned. No root required. To
uninstall, remove the three installed files listed below:

```
~/.local/bin/noctalia-widget-manager
~/.local/share/applications/noctalia-widget-manager.desktop
~/.local/share/icons/hicolor/256x256/apps/noctalia-widget-manager.png
```

## Usage

Run from source:

```bash
python3 main.py
```

Or launch the installed app from your launcher (or `noctalia-widget-manager`).

Edit the config path at the top of `main.py` if your Noctalia config lives
somewhere other than `~/.config/noctalia/settings.json`.

After saving, restart the shell to apply changes (Quickshell may not hot-reload
the config):

```bash
killall noctalia-shell && qs -c noctalia-shell &
```

## How it works

The app parses `settings.json`, shows the `bar.widgets.left/center/right`
arrays as lists, and on **Save** writes them back in the current order. Widget
entries are moved as whole objects, so all of their settings are preserved.
The original file is copied to `settings.json.bak` before every save.

## Project layout

```
main.py                         The application (single file)
build.sh                        Builds the standalone binary with PyInstaller
install.sh                      Installs the binary + launcher entry
noctalia-widget-manager.spec    PyInstaller spec (one-file, windowed)
tools/make_icon.py              Renders the launcher icon (PNG)
data/                           Generated icon + .desktop launcher template
.venv/                          Build venv (created by build.sh, gitignored)
dist/                           Built binary (created by build.sh, gitignored)
.gitignore                      Excludes Python caches and personal config files
```
