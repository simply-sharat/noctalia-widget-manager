# Noctalia Widget Manager

A small PySide6 (Qt6) desktop app to view and reorder the bar widgets in
[Noctalia](https://noctalia.dev) v5's TOML configuration.

Noctalia's plugin manager always appends new plugin widgets to the **end** of
the bar's `end` lane, so they land at the far right (after the tray and
control center). This tool lets you fix the arrangement: reorder widgets, move
them between the `start` / `center` / `end` lanes, and save the result.

Works with **Noctalia v5** (the native C++/TOML rewrite). For the legacy v4
Quickshell/JSON shell, see the `v4` tag.

## Features

- Pick which `[bar.*]` to edit (v5 supports multiple named bars)
- Three columns matching the bar lanes: **Start**, **Center**, **End**
- Reorder within a lane with the ▲ / ▼ buttons or drag-and-drop
- Move widgets between lanes with the ◀ / ▶ buttons or drag-and-drop
- **Reload from Disk** — discard unsaved changes and re-read the config
- **Save** — writes the selected bar's `start` / `center` / `end` lanes into
  the hand-written config file that currently defines them (e.g.
  `config.toml`), preserving every widget's settings and taking a
  `.bak` backup of that file first

## Requirements

- Python 3.10+
- PySide6 and tomlkit
  (`pip install PySide6 tomlkit`, or on Arch
  `sudo pacman -S python-pyside6` and `python -m pip install tomlkit`)

Only needed to run `main.py` directly. The packaged binary (see below) is
self-contained and needs neither Python, PySide6, nor tomlkit.

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

The config location is resolved like Noctalia itself: the config directory is
`$NOCTALIA_CONFIG_HOME/noctalia` → `$XDG_CONFIG_HOME/noctalia` →
`~/.config/noctalia`, and the override file is
`$NOCTALIA_STATE_HOME/noctalia/settings.toml` →
`$XDG_STATE_HOME/noctalia/settings.toml` → `~/.local/state/noctalia/settings.toml`.

After saving, Noctalia hot-reloads the config automatically. If you want to
force it:

```bash
noctalia msg config-reload
```

## How it works

The app replicates v5's config stack: it reads every `*.toml` in the config
directory (sorted, non-recursive, honoring `[include]`), then layers the
GUI-managed `settings.toml` override on top. It shows the `start` / `center` /
`end` arrays of the selected `[bar.*]` table as lists, and on **Save** writes
those arrays for that bar back into the hand-written config file that owns the
bar's lanes (the last file in load order that defines them, e.g. `config.toml`),
preserving all other keys. Widget entries are just names, so their settings (in
`[widget.<name>]` tables) are never touched.

Notes:

- Lane entries are opaque names, including plugin ids
  (`<author>/<plugin>:<entry>`) and capsule-group references (`group:<id>`);
  all are preserved as-is.
- Changes are written to `~/.config/noctalia/*.toml` — the layer Noctalia
  never rewrites. The app deliberately does **not** write to
  `~/.local/state/noctalia/settings.toml` (the GUI override file): Noctalia
  owns that file and may strip values from it when it re-saves.
- If `settings.toml` currently overrides the bar's lanes (from a previous
  Settings-GUI reorder), the app warns that its changes are shadowed until
  those keys are removed from `settings.toml`.
- If no config file defines the bar's lanes, the app writes to a new
  `config.toml` (or `zzz-noctalia-widget-manager.toml` when other config files
  exist, so it merges last).
- Per-monitor lane overrides (`[bar.<name>.monitor.<mon>]`) are not edited;
  reordering affects the base bar.

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
