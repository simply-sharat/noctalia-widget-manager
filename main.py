#!/usr/bin/env python3
"""Noctalia Widget Manager.

View and reorder the bar widgets (start / center / end) in Noctalia v5's
TOML configuration. Reads the merged config (every *.toml in the config dir,
plus the GUI-managed override file) and writes reorder changes back to the
override file, mirroring what the Settings GUI would write.
"""

import os
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

import tomlkit
from tomlkit.exceptions import ParseError, TOMLKitError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

SECTIONS = ["start", "center", "end"]
SECTION_TITLES = {"start": "Start", "center": "Center", "end": "End"}


# ---- config discovery & merge ---------------------------------------------


def noctalia_config_dir():
    root = os.environ.get("NOCTALIA_CONFIG_HOME") or os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(root).expanduser() / "noctalia"


def noctalia_state_file():
    root = os.environ.get("NOCTALIA_STATE_HOME") or os.environ.get("XDG_STATE_HOME") or "~/.local/state"
    return Path(root).expanduser() / "noctalia" / "settings.toml"


def deep_merge(base, override):
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _expand_path(base, entry):
    expanded = os.path.expandvars(os.path.expanduser(str(entry)))
    path = Path(expanded)
    if not path.is_absolute():
        path = base / path
    return path


def _included_files(base, entry):
    path = _expand_path(base, entry)
    if path.is_dir():
        return sorted(path.glob("*.toml"))
    return [path]


def _load_toml(path, merged, stack, prov, order, honor_include=True):
    path = path.resolve()
    if path in stack:
        return False
    stack.add(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    doc = tomlkit.parse(text)
    order.append(path)

    stop = False
    if honor_include:
        include = doc.get("include")
        if isinstance(include, Mapping):
            files = include.get("files")
            if isinstance(files, list):
                for entry in files:
                    for child in _included_files(path.parent, entry):
                        _load_toml(child, merged, stack, prov, order)
            if include.get("autoload") is False:
                stop = True

    own = {key: value for key, value in doc.items() if key != "include"}
    deep_merge(merged, own)

    bar = own.get("bar")
    if isinstance(bar, Mapping):
        for bname, btable in bar.items():
            if isinstance(btable, Mapping):
                for section in SECTIONS:
                    if section in btable:
                        prov[(bname, section)] = path

    stack.discard(path)
    return stop


def load_config(config_dir, state_file):
    merged = {}
    prov = {}
    order = []
    stack = set()
    for path in sorted(config_dir.glob("*.toml")):
        if _load_toml(path, merged, stack, prov, order):
            break
    if state_file.exists():
        _load_toml(state_file, merged, stack, prov, order, honor_include=False)
    return merged, prov, order


def _ensure_table(parent, name):
    table = parent.get(name)
    if not isinstance(table, Mapping):
        table = tomlkit.table()
        parent[name] = table
    return table


def write_lanes(path, bar_name, lanes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    else:
        doc = tomlkit.document()

    bar = _ensure_table(doc, "bar")
    table = _ensure_table(bar, bar_name)
    for section in SECTIONS:
        table[section] = list(lanes[section])

    backup = path.with_suffix(".toml.bak")
    if path.exists():
        shutil.copy2(path, backup)
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _bar_table(path, bar_name):
    if not path.exists():
        return {}
    doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    bar = doc.get("bar", {})
    if not isinstance(bar, Mapping):
        return {}
    return bar.get(bar_name, {})


# ---- UI --------------------------------------------------------------------


class SectionPanel(QFrame):
    def __init__(self, title, move_cb, parent=None):
        super().__init__(parent)
        self.move_cb = move_cb

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel(title)
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDrop)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)

        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        self.up_btn = self._button("Up", "▲", lambda: self.move_cb("up"))
        self.down_btn = self._button("Down", "▼", lambda: self.move_cb("down"))
        self.left_btn = self._button("To Start", "◀", lambda: self.move_cb("left"))
        self.right_btn = self._button("To End", "▶", lambda: self.move_cb("right"))
        buttons.addWidget(self.up_btn)
        buttons.addWidget(self.down_btn)
        buttons.addWidget(self.left_btn)
        buttons.addWidget(self.right_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _button(self, tooltip, glyph, handler):
        btn = QPushButton(glyph)
        btn.setToolTip(tooltip)
        btn.setFixedWidth(40)
        btn.clicked.connect(handler)
        return btn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noctalia Widget Manager")
        self.resize(780, 460)

        self.data = None
        self.bar = None
        self.config_dir = noctalia_config_dir()
        self.state_file = noctalia_state_file()

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        top = QHBoxLayout()
        top.addWidget(QLabel("Bar:"))
        self.bar_combo = QComboBox()
        self.bar_combo.currentTextChanged.connect(self._select_bar)
        top.addWidget(self.bar_combo)
        top.addStretch()
        outer.addLayout(top)

        rows = QHBoxLayout()
        rows.setSpacing(10)
        self.panels = []
        for i, section in enumerate(SECTIONS):
            panel = SectionPanel(SECTION_TITLES[section], lambda action, idx=i: self._move(idx, action))
            panel.left_btn.setEnabled(i > 0)
            panel.right_btn.setEnabled(i < len(SECTIONS) - 1)
            panel.list.model().rowsInserted.connect(lambda *_, p=panel: self._sync_panel_buttons(p))
            panel.list.model().rowsRemoved.connect(lambda *_, p=panel: self._sync_panel_buttons(p))
            self.panels.append(panel)
            rows.addWidget(panel, 1)
        outer.addLayout(rows, 1)

        actions = QHBoxLayout()
        reload_btn = QPushButton("Reload from Disk")
        reload_btn.clicked.connect(self.reload)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save)
        actions.addStretch()
        actions.addWidget(reload_btn)
        actions.addWidget(save_btn)
        outer.addLayout(actions)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("")

        self.load()

    # ---- loading / saving -------------------------------------------------

    def load(self):
        self.prov = {}
        self.order = []
        try:
            self.data, self.prov, self.order = load_config(self.config_dir, self.state_file)
        except ParseError as exc:
            QMessageBox.critical(self, "Error", f"Invalid TOML in Noctalia config:\n{exc}")
            self.data = {}
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Could not read config:\n{exc}")
            self.data = {}

        bars = sorted(self.data.get("bar", {}))
        self.bar_combo.blockSignals(True)
        self.bar_combo.clear()
        self.bar_combo.addItems(bars)
        self.bar_combo.blockSignals(False)

        if not bars:
            self._clear_panels()
            if not self.config_dir.exists():
                QMessageBox.warning(self, "No config found",
                                    f"Config directory not found:\n{self.config_dir}")
            else:
                QMessageBox.warning(self, "No bars found",
                                    f"No [bar.*] tables found in:\n{self.config_dir}")
            self.statusBar().showMessage("No Noctalia v5 config found", 5000)
            return
        self._select_bar(self.bar_combo.currentText())
        self.statusBar().showMessage(
            f"Loaded {self.config_dir} + {self.state_file.name}", 4000)

    def reload(self):
        self.load()

    def save(self):
        if self.data is None or not self.bar:
            return
        lanes = {}
        for i, section in enumerate(SECTIONS):
            lst = self.panels[i].list
            lanes[section] = [self._item_name(lst.item(r))
                              for r in range(lst.count())]
        target, shadowed = self._lane_target(self.bar)
        if target is None:
            QMessageBox.critical(
                self, "Error",
                f"Could not find a config file to edit for bar {self.bar!r}.")
            return
        if shadowed:
            QMessageBox.warning(
                self, "Changes will be shadowed",
                f"{self.state_file.name} currently overrides the {self.bar!r} "
                f"lanes, so changes written to {target.name} will not take "
                f"effect until those keys are removed from {self.state_file.name}.")
        try:
            write_lanes(target, self.bar, lanes)
        except (TOMLKitError, OSError) as exc:
            QMessageBox.critical(self, "Error", f"Could not write {target}:\n{exc}")
            return
        self.statusBar().showMessage(
            f"Saved {self.bar} lanes to {target} (backup: {target.name}.bak)", 6000)

    # ---- save target selection -------------------------------------------

    def _is_state(self, path):
        return path == self.state_file.resolve()

    def _lane_target(self, bar_name):
        owners = {path for (b, _s), path in self.prov.items() if b == bar_name}
        cfg_owners = [p for p in owners if not self._is_state(p)]
        shadowed = any(self._is_state(p) for p in owners)

        if cfg_owners:
            for p in reversed(self.order):
                if p in cfg_owners:
                    return p, shadowed
            return None, shadowed

        for p in self.order:
            if self._is_state(p):
                break
            if isinstance(_bar_table(p, bar_name), Mapping):
                return p, shadowed

        existing = sorted(p.name for p in self.config_dir.glob("*.toml"))
        name = "zzz-noctalia-widget-manager.toml" if existing else "config.toml"
        return self.config_dir / name, shadowed

    # ---- bar selection ----------------------------------------------------

    def _clear_panels(self):
        for panel in self.panels:
            panel.list.clear()

    def _select_bar(self, name):
        self.bar = name
        bar = self.data.get("bar", {}).get(name, {}) if name else {}
        for i, section in enumerate(SECTIONS):
            self.panels[i].list.clear()
            for entry in bar.get(section, []):
                self._add_item(self.panels[i].list, str(entry))

    # ---- item helpers -----------------------------------------------------

    def _add_item(self, lst, name):
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setToolTip(self._describe(name))
        lst.addItem(item)

    @staticmethod
    def _item_name(item):
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _describe(self, name):
        widget = self.data.get("widget", {}).get(name) if self.data else None
        if name.startswith("group:"):
            return "Capsule group entry"
        if isinstance(widget, Mapping):
            widget_type = str(widget.get("type", ""))
            if widget_type and widget_type != name:
                return f"widget {name!r} of type {widget_type}"
        return name

    # ---- reordering -------------------------------------------------------

    def _move(self, section_idx, action):
        lst = self.panels[section_idx].list
        row = lst.currentRow()
        if row < 0:
            self.statusBar().showMessage("Select a widget first", 2500)
            return

        if action == "up" and row > 0:
            item = lst.takeItem(row)
            lst.insertItem(row - 1, item)
            lst.setCurrentRow(row - 1)
        elif action == "down" and row < lst.count() - 1:
            item = lst.takeItem(row)
            lst.insertItem(row + 1, item)
            lst.setCurrentRow(row + 1)
        elif action == "left" and section_idx > 0:
            self._move_across(section_idx, section_idx - 1)
        elif action == "right" and section_idx < len(SECTIONS) - 1:
            self._move_across(section_idx, section_idx + 1)

    def _move_across(self, src_idx, dst_idx):
        src = self.panels[src_idx].list
        dst = self.panels[dst_idx].list
        row = src.currentRow()
        item = src.takeItem(row)
        dst.addItem(item)
        dst.setCurrentItem(item)

    def _sync_panel_buttons(self, panel):
        lst = panel.list
        has_items = lst.count() > 0
        panel.up_btn.setEnabled(has_items)
        panel.down_btn.setEnabled(has_items)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
