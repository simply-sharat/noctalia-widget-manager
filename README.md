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

## Usage

```bash
python3 main.py
```

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
main.py       The application (single file)
.gitignore    Excludes Python caches and personal config files
```
